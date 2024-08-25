import gi
import requests
import sys
import threading
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

def list_available_cameras(server_url):
    try:
        response = requests.get(f"{server_url}/list_cameras")
        response.raise_for_status()
        cameras = response.json()
        return cameras
    except Exception as e:
        print(f"Error fetching camera list: {e}")
        return []

def on_eos(bus, msg, loop):
    print("End of stream")
    loop.quit()

def on_error(bus, msg, loop):
    err, debug = msg.parse_error()
    if "Output window was closed" in str(err):
        print("Window was closed by the user. Exiting...")
    else:
        print(f"Error: {err}, {debug}")
    loop.quit()

def start_stream(rtsp_url):
    pipeline_str = f'rtspsrc location={rtsp_url} latency=0 ! decodebin ! autovideosink'
    pipeline = Gst.parse_launch(pipeline_str)

    loop = GLib.MainLoop()

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message::eos", on_eos, loop)
    bus.connect("message::error", on_error, loop)

    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except KeyboardInterrupt:
        print("Stream interrupted, stopping...")
    finally:
        pipeline.set_state(Gst.State.NULL)

def main():
    server_url = "http://127.0.0.1:5000" 

    cameras = list_available_cameras(server_url)
    if not cameras:
        print("No cameras available or failed to fetch camera list.")
        return

    print("Available cameras:")
    for idx, camera in enumerate(cameras):
        print(f"{idx}: {camera}")

    stream_name = input("Enter the name of the camera to stream: ").strip()

    if stream_name not in cameras:
        print("Error: Camera name not found.")
        return

    rtsp_url = f'rtsp://127.0.0.1:8554/{stream_name}'

    # Start the stream in a separate thread
    stream_thread = threading.Thread(target=start_stream, args=(rtsp_url,))
    stream_thread.start()

if __name__ == '__main__':
    main()
