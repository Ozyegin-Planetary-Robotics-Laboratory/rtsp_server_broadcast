import gi
import os
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gst, GstRtspServer, GLib

class CameraServerHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.camera_server = kwargs.pop('camera_server')
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/list_cameras':
            camera_list = self.camera_server.get_camera_list()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(camera_list).encode())
        else:
            self.send_response(404)
            self.end_headers()

class DynamicCameraRTSPServer:
    def __init__(self):
        Gst.init(None)
        self.server = GstRtspServer.RTSPServer()
        self.server.set_service("8554")
        self.mounts = self.server.get_mount_points()
        self.camera_streams = {}  # Store active camera streams
        self.camera_usage = {}  # Track which cameras are in use

        # Initialize camera list lock and dictionary
        self.camera_list_lock = threading.Lock()
        self.camera_list = {}

        # Start monitoring for camera connections
        threading.Thread(target=self.monitor_cameras, daemon=True).start()

        # Start the HTTP server
        self.http_server = HTTPServer(('0.0.0.0', 5000),
                                     lambda *args, **kwargs: CameraServerHandler(*args, camera_server=self, **kwargs))
        threading.Thread(target=self.start_http_server, daemon=True).start()

        self.server.attach(None)
        print("RTSP server is running. Monitoring for camera connections...")
        print("HTTP server is running on port 5000...")

    def get_camera_usb_info(self, device_id):
        try:
            # Run udevadm to get device information
            command = f"udevadm info --query=all --name=/dev/video{device_id}"
            result = subprocess.run(command.split(), capture_output=True, text=True)

            # Check for errors
            if result.returncode != 0:
                print(f"Error running udevadm: {result.stderr}")
                return None, None

            # Extract vendor and product ID from the output
            vendor_id, product_id = None, None
            for line in result.stdout.splitlines():
                if "ID_VENDOR_ID=" in line:
                    vendor_id = line.split("=")[1]
                elif "ID_MODEL_ID=" in line:
                    product_id = line.split("=")[1]

            if vendor_id and product_id:
                return vendor_id, product_id
            else:
                print("Vendor ID or Product ID not found")
                return None, None

        except Exception as e:
            print(f"An error occurred: {e}")
            return None, None

    def is_camera_streamable(self, device_path, camera_name):
        try:
            # Attempt to open the camera using GStreamer without disrupting availability
            pipeline_str = f"v4l2src device={device_path} ! videoconvert ! fakesink"
            pipeline = Gst.parse_launch(pipeline_str)
            pipeline.set_state(Gst.State.PLAYING)

            # Wait for a short period to determine if the pipeline can enter PLAYING state
            bus = pipeline.get_bus()
            msg = bus.timed_pop_filtered(1000000000, Gst.MessageType.ERROR | Gst.MessageType.ASYNC_DONE)

            # Set the pipeline to NULL state to release resources
            pipeline.set_state(Gst.State.NULL)

            # If there's no error message, the camera is streamable
            return msg is None or msg.type != Gst.MessageType.ERROR
        except Exception as e:
            print(f"Error checking if camera is streamable: {e}")
            return False

    def enumerate_cameras(self):
        camera_list = {}
        for device_id in range(10):
            device_path = f"/dev/video{device_id}"
            if os.path.exists(device_path):
                # Get the USB vendor and product IDs
                vendor_id, product_id = self.get_camera_usb_info(device_id)
                # Determine the camera name
                if vendor_id == "1234" and product_id == "abcd":
                    camera_name = "web"
                elif vendor_id == "5678" and product_id == "efgh":
                    camera_name = "usb"
                else:
                    camera_name = f"camera_{device_id}"

                # Check if the camera is streamable
                if self.is_camera_streamable(device_path, camera_name) or self.camera_usage.get(camera_name, False):
                    camera_list[camera_name] = {
                        "device_path": device_path,
                        "in_use": camera_name in self.camera_usage
                    }

        return camera_list

    def monitor_cameras(self):
        while True:
            current_cameras = self.enumerate_cameras()

            with self.camera_list_lock:
                # Update the camera list
                self.camera_list = current_cameras

            # Add new camera streams
            for name, info in current_cameras.items():
                if name not in self.camera_streams:
                    print(f"New camera detected: {name} ({info['device_path']})")
                    self.add_camera_stream(name, info['device_path'])
                    self.camera_streams[name] = info['device_path']
                    self.camera_usage[name] = True

            # Remove disconnected camera streams, but only if they are not in use
            for name in list(self.camera_streams):
                if name not in current_cameras and self.camera_usage.get(name, False):
                    print(f"Camera disconnected: {name}")
                    self.remove_camera_stream(name)
                    del self.camera_streams[name]
                    if name in self.camera_usage:
                        del self.camera_usage[name]

            time.sleep(5)  # Check every 5 seconds (adjust as needed)

    def add_camera_stream(self, name, device_path):
        factory = GstRtspServer.RTSPMediaFactory()
        if "zed" in name.lower():
            factory.set_launch(
                f'( v4l2src device={device_path} ! videoconvert ! videocrop right=2208 ! videoconvert ! x264enc tune=zerolatency bitrate=1000 speed-preset=superfast ! h264parse ! rtph264pay config-interval=10 name=pay0 pt=96 )'
            )
        else:
            factory.set_launch(
                f'( v4l2src device={device_path} ! videoconvert ! x264enc tune=zerolatency bitrate=1000 speed-preset=superfast ! h264parse ! rtph264pay config-interval=10 name=pay0 pt=96 )'
            )
        factory.set_shared(True)
        self.mounts.add_factory(f"/{name}", factory)
        print(f"Started streaming: rtsp://127.0.0.1:8554/{name}")

    def remove_camera_stream(self, name):
        self.mounts.remove_factory(f"/{name}")
        print(f"Stopped streaming: {name}")

    def get_camera_list(self):
        with self.camera_list_lock:
            return self.camera_list

    def start_http_server(self):
        self.http_server.serve_forever()

    def run(self):
        loop = GLib.MainLoop()
        loop.run()

if __name__ == '__main__':
    server = DynamicCameraRTSPServer()
    server.run()
