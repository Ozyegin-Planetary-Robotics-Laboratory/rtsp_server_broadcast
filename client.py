import cv2

def view_rtsp_stream(rtsp_url):
    # Open a connection to the RTSP stream
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print(f"Error: Could not open video stream from {rtsp_url}")
        return

    print(f"Successfully connected to {rtsp_url}")

    while True:
        # Read a frame from the stream
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from stream")
            break

        # Display the frame
        cv2.imshow('RTSP Stream', frame)

        # Exit if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    rtsp_url = 'rtsp://127.0.0.1:8554/camera_2'  # Replace with your RTSP stream URL
    view_rtsp_stream(rtsp_url)
