# Social TUI Visualizer

This web-based component provides a graphical visualization of the data from the Social TUI application. It connects to a WebSocket server to receive post data in real-time as you browse in the TUI.

## Features

- **Real-time Updates**: See post details instantly as you select them in the TUI.
- **Media Previews**: View images and videos from posts directly in the browser.
- **Engagement Chart**: Visualize the timeline of post reactions with an interactive chart.

## How to Use

1.  **Install Dependencies**:
    The TUI now requires the `websockets` library. Make sure it's installed in your Python environment. If you are using `uv`, it should be installed automatically from `pyproject.toml`.

2.  **Start the WebSocket Server**:
    In your terminal, run the following command from the root of the `social-tui` project:
    ```bash
    python websocket_server.py
    ```
    The server will start and listen for connections on `ws://localhost:8765`.

3.  **Open the Visualizer**:
    Open the `index.html` file in your web browser.
    ```bash
    open web_visualization/index.html
    ```

4.  **Run the TUI with WebSocket Support**:
    Run the `interactive_posts.py` script with the `--websocket-port` argument:
    ```bash
    ./interactive_posts.py --websocket-port 8765
    ```

Now, when you select a post in the TUI, its details will be sent to the web visualizer and displayed in your browser.
