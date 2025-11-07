import socket
import threading
import time
import os
from flask import Flask, request, jsonify, render_template_string

clients = {}
messages = []
lock = threading.Lock()

app = Flask(__name__)


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Client Control Panel</title>
    <style>
        body { font-family: Arial; background: #111; color: #eee; text-align: center; }
        h1 { color: #0f0; }
        select, input { padding: 6px; margin: 5px; border-radius: 4px; border: none; }
        button { background: #0f0; color: #000; padding: 6px 10px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #3f3; }
        #clients { color: #0ff; font-size: 15px; }
        #log { text-align: left;white-space: pre; margin: 20px auto; width: 80%; height: 300px; background: #000; color: #0f0; overflow-y: auto; border: 1px solid #0f0; padding: 10px; border-radius: 6px; }
    </style>
</head>
<body>
    <h1>Connected Clients</h1>
    <div id="clients"></div>
    <br>
    <select id="clientSelect"></select>
    <br>
    <input id="msg" placeholder="Enter message" />
    <button onclick="sendMsg()">Send</button>

    <h2>Messages</h2>
    <div id="log"></div>
<script>
    let autoScroll = true; // auto-scroll unless user scrolls up manually

async function loadClients() {
    const res = await fetch("/clients");
    const data = await res.json();
    const select = document.getElementById("clientSelect");
    const div = document.getElementById("clients");

    // Remember currently selected client
    const prevSelected = select.value;

    select.innerHTML = "";
    div.innerHTML = data.length ? "Online clients: " + data.length : "No clients connected";

    let found = false;
    data.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.address;
        if (c.id === prevSelected) {
            opt.selected = true;
            found = true;
        }
        select.appendChild(opt);
    });

    // If the previously selected client disappeared
    if (!found && data.length) {
        select.selectedIndex = 0;
    }
}


    async function loadMessages() {
        const res = await fetch("/messages");
        const data = await res.json();
        const log = document.getElementById("log");

        const atBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 20;

        // Only refresh HTML if there are new messages
        const oldText = log.dataset.lastText || "";
        const newText = data.map(m => "[" + escapeHTML(m.time) + "] " + escapeHTML(m.text)).join("<br>");
        if (newText !== oldText) {
            log.innerHTML = newText;
            log.dataset.lastText = newText;
            if (autoScroll && atBottom) {
                log.scrollTop = log.scrollHeight;
            }
        }
    }

    function escapeHTML(str) {
        return str.replace(/&/g, "&amp;")
                  .replace(/</g, "&lt;")
                  .replace(/>/g, "&gt;");
    }

    async function sendMsg() {
        const id = document.getElementById("clientSelect").value;
        const msg = document.getElementById("msg").value;
        if (!id || !msg) return alert("Select client and enter message");
        await fetch(`/send?id=${id}&msg=${encodeURIComponent(msg)}`);
        document.getElementById("msg").value = "";
    }

    // detect user scroll — disable auto-scroll if scrolled up
    const logDiv = document.getElementById("log");
    logDiv.addEventListener("scroll", () => {
        const nearBottom = logDiv.scrollTop + logDiv.clientHeight >= logDiv.scrollHeight - 20;
        autoScroll = nearBottom;
    });

    setInterval(loadClients, 2000);
    setInterval(loadMessages, 1000);
    loadClients();
    loadMessages();
</script>

</body>
</html>
"""


def handle_client(client_socket, client_address):
    with lock:
        cid = str(time.time())
        clients[cid] = {"socket": client_socket, "address": f"{client_address[0]}:{client_address[1]}"}
    print(f"[+] {client_address} connected as {cid}")

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            msg = data.decode(errors="ignore").strip()
            log_entry = {"time": time.strftime("%H:%M:%S"), "text": f"[{client_address}] {msg}"}
            with lock:
                messages.append(log_entry)
                if len(messages) > 1000:
                    messages.pop(0)
            print(f"[{client_address}] {msg}")
    except:
        pass
    finally:
        with lock:
            if cid in clients:
                del clients[cid]
        client_socket.close()
        print(f"[-] {client_address} disconnected.")


@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

@app.route("/clients")
def list_clients():
    with lock:
        client_list = [{"id": cid, "address": info["address"]} for cid, info in clients.items()]
    return jsonify(client_list)

@app.route("/messages")
def get_messages():
    with lock:
        return jsonify(messages[-200:])  

@app.route("/send")
def send_message():
    cid = request.args.get("id")
    msg = request.args.get("msg")
    if not cid or not msg:
        return jsonify({"error": "Missing id or msg"}), 400

    with lock:
        client = clients.get(cid)
        if not client:
            return jsonify({"error": "Client not found"}), 404
        try:
            client["socket"].sendall(msg.encode())
        except:
            return jsonify({"error": "Send failed"}), 500

    print(f"[API] Sent '{msg}' to {client['address']}")
    return jsonify({"status": "sent", "to": client["address"]})



def tcp_server():
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 12345
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen(5)
    print(f"[TCP] Listening on {SERVER_HOST}:{SERVER_PORT}")

    while True:
        client_socket, client_address = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()



if __name__ == "__main__":
    threading.Thread(target=tcp_server, daemon=True).start()
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

