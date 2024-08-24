import gi
import sys
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(None)

def on_eos(bus, msg, loop):
    print("End of stream")
    loop.quit()

def on_error(bus, msg, loop):
    err, debug = msg.parse_error()
    # Handle the specific "Output window was closed" error gracefully
    if "Output window was closed" in str(err):
        print("Window was closed by the user. Exiting...")
    else:
        print(f"Error: {err}, {debug}")
    loop.quit()

def main():
    # Define the pipeline to play the RTSP stream
    stream_name = input("Enter the stream name (e.g., 'zed' or 'camera_0'): ")
    rtsp_url = f'rtsp://127.0.0.1:8554/{stream_name}'

    pipeline_str = f'rtspsrc location={rtsp_url} latency=0 ! decodebin ! autovideosink'
    pipeline = Gst.parse_launch(pipeline_str)

    # Set up the GLib main loop
    loop = GLib.MainLoop()

    # Get the pipeline bus to monitor events
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message::eos", on_eos, loop)
    bus.connect("message::error", on_error, loop)

    # Start playing the pipeline
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except KeyboardInterrupt:
        print("Stream interrupted, stopping...")
    finally:
        pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    main()
