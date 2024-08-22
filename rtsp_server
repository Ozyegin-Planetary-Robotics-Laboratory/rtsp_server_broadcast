import gi
import os
import time
import threading
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import GObject, Gst, GstRtspServer

class DynamicCameraRTSPServer:
    def __init__(self):
        Gst.init(None)
        self.server = GstRtspServer.RTSPServer()
        self.server.set_service("8554")
        self.mounts = self.server.get_mount_points()
        self.camera_streams = {}  # Store active camera streams

        # Start monitoring for camera connections
        threading.Thread(target=self.monitor_cameras, daemon=True).start()

        self.server.attach(None)
        print("RTSP server is running. Monitoring for camera connections...")

    def enumerate_cameras(self):
        camera_list = {}
        for device_id in range(10):
            device_path = f"/dev/video{device_id}"
            if os.path.exists(device_path):
                camera_name = f"camera_{device_id}"
                symbolic_link = os.readlink(f'/sys/class/video4linux/video{device_id}/device')
                if "zed" in symbolic_link.lower():
                    camera_name = "zed"
                elif "usb" in symbolic_link.lower():
                    camera_name = "usb"
                camera_list[camera_name] = device_path
        return camera_list

    def monitor_cameras(self):
        while True:
            current_cameras = self.enumerate_cameras()

            # Add new camera streams
            for name, device_path in current_cameras.items():
                if name not in self.camera_streams:
                    print(f"New camera detected: {name} ({device_path})")
                    self.add_camera_stream(name, device_path)
                    self.camera_streams[name] = device_path

            # Remove disconnected camera streams
            for name in list(self.camera_streams):
                if name not in current_cameras:
                    print(f"Camera disconnected: {name}")
                    self.remove_camera_stream(name)
                    del self.camera_streams[name]

            time.sleep(5)  # Check every 5 seconds (adjust as needed)

    def add_camera_stream(self, name, device_path):
        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch(
            f'( v4l2src device={device_path} ! videoconvert ! x264enc tune=zerolatency bitrate=1000 speed-preset=superfast ! h264parse ! rtph264pay config-interval=10 name=pay0 pt=96 )'
        )
        factory.set_shared(True)
        self.mounts.add_factory(f"/{name}", factory)
        print(f"Started streaming: rtsp://127.0.0.1:8554/{name}")

    def remove_camera_stream(self, name):
        self.mounts.remove_factory(f"/{name}")
        print(f"Stopped streaming: {name}")

    def run(self):
        loop = GObject.MainLoop()
        loop.run()

if __name__ == '__main__':
    server = DynamicCameraRTSPServer()
    server.run()
