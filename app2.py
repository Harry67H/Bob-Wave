from flask import Flask, render_template_string, request, send_file
from pydub import AudioSegment
import io
import base64
import json

app = Flask(__name__)

# Store projects (each project has its own layers)
projects = {}

html = """
<!DOCTYPE html>
<html>
<head>
  <title>Bob Wave</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #111;
      color: white;
      text-align: center;
    }
    h1 {
      font-size: 40px;
    }
    .bob {
      color: #b57edc; /* light purple */
      font-family: "Comic Sans MS", cursive, sans-serif;
    }
    .wave {
      font-family: "Comic Sans MS", cursive, sans-serif;
    }
    button {
      margin: 5px;
      padding: 8px 15px;
      font-size: 16px;
      border-radius: 8px;
      border: none;
      cursor: pointer;
    }
    .layer {
      margin: 10px;
      background: #222;
      padding: 10px;
      border-radius: 10px;
    }
    .layer-controls {
      display: flex;
      align-items: center;
      justify-content: flex-start;
      margin-bottom: 5px;
    }
    .eye, .delete {
      cursor: pointer;
      font-size: 20px;
      margin: 0 5px;
    }
    .volume {
      width: 100px;
      margin: 0 10px;
    }
    .downloads, .layers {
      margin: 20px;
      padding: 10px;
      border: 2px dashed #666;
      border-radius: 10px;
      min-height: 100px;
    }
    .downloads h2 {
      margin: 0;
    }
    .download-item {
      margin: 5px;
      padding: 5px;
      background: #333;
      border-radius: 5px;
      cursor: grab;
    }
    .projects {
      margin: 20px;
    }
    .project-tab {
      display: inline-block;
      margin: 5px;
      padding: 5px 10px;
      background: #333;
      border-radius: 5px;
      cursor: pointer;
    }
    .active {
      background: #555;
    }
  </style>
</head>
<body>
  <h1><span class="bob">Bob</span> <span class="wave">Wave</span></h1>

  <button id="recordBtn">🎤</button>
  <button id="playBtn">▶️</button>
  <button id="saveBtn">💾 Save</button>
  <button id="openBtn">📂 Open Project</button>

  <div class="projects" id="projects"></div>

  <div class="downloads" id="downloads" ondrop="dropDownload(event)" ondragover="allowDrop(event)">
    <h2>Downloads (drag files here)</h2>
  </div>

  <div class="layers" id="layers" ondrop="dropToLayers(event)" ondragover="allowDrop(event)">
    <h2>Layers</h2>
  </div>

  <script src="https://unpkg.com/wavesurfer.js"></script>
  <script>
    let audioChunks = [];
    let mediaRecorder;
    let layerId = 0;
    let layers = [];
    let projects = {};
    let currentProject = "default";
    let isPlaying = false; // for play toggle
    projects[currentProject] = [];

    function refreshProjects() {
      let div = document.getElementById("projects");
      div.innerHTML = "";
      for (let p in projects) {
        let tab = document.createElement("div");
        tab.className = "project-tab" + (p === currentProject ? " active" : "");
        tab.textContent = p;
        tab.onclick = () => {
          currentProject = p;
          layers = projects[p];
          renderLayers();
          refreshProjects();
        };
        div.appendChild(tab);
      }
    }

    refreshProjects();

    document.getElementById("recordBtn").onclick = async () => {
      if (!mediaRecorder || mediaRecorder.state === "inactive") {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = e => {
          audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
          const blob = new Blob(audioChunks, { type: 'audio/wav' });
          audioChunks = [];
          uploadLayer(blob, layerId);
          addLayer(blob, layerId);
          layerId++;
        };

        mediaRecorder.start();
      } else {
        mediaRecorder.stop();
      }
    };

    function uploadLayer(blob, id) {
      const reader = new FileReader();
      reader.onloadend = () => {
        fetch("/upload", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: id, audio: reader.result, project: currentProject })
        });
      };
      reader.readAsDataURL(blob);
    }

    function addLayer(blob, id) {
      if (layers.length >= 5) return;
      const url = URL.createObjectURL(blob);
      const layer = { id, url, visible: true, volume: 1 };
      layers.push(layer);
      projects[currentProject] = layers;
      renderLayers();
    }

    function renderLayers() {
      let container = document.getElementById("layers");
      container.innerHTML = "<h2>Layers</h2>";

      layers.forEach(l => {
        const div = document.createElement("div");
        div.className = "layer";
        div.dataset.id = l.id;

        // controls row
        const controls = document.createElement("div");
        controls.className = "layer-controls";

        const eye = document.createElement("span");
        eye.textContent = l.visible ? "👁️" : "🚫";
        eye.className = "eye";
        eye.onclick = () => {
          l.visible = !l.visible;
          renderLayers();
        };

        const del = document.createElement("span");
        del.textContent = "❌";
        del.className = "delete";
        del.onclick = () => {
          layers = layers.filter(x => x.id !== l.id);
          projects[currentProject] = layers;
          renderLayers();
        };

        const volume = document.createElement("input");
        volume.type = "range";
        volume.min = 0;
        volume.max = 2;
        volume.step = 0.1;
        volume.value = l.volume;
        volume.className = "volume";
        volume.oninput = () => {
          l.volume = volume.value;
          l.wavesurfer.setVolume(l.volume);
          l.wavesurfer.zoom(l.volume * 20 + 10); // louder-looking waveform
        };

        controls.appendChild(eye);
        controls.appendChild(del);
        controls.appendChild(volume);

        const waveform = document.createElement("div");
        const wavesurfer = WaveSurfer.create({
          container: waveform,
          waveColor: 'violet',
          progressColor: 'purple'
        });
        wavesurfer.load(l.url);
        wavesurfer.setVolume(l.volume);
        l.wavesurfer = wavesurfer;

        div.appendChild(controls);
        div.appendChild(waveform);
        container.appendChild(div);
      });
    }

    document.getElementById("playBtn").onclick = () => {
      if (!isPlaying) {
        layers.forEach(l => {
          if (l.visible) l.wavesurfer.play();
        });
        isPlaying = true;
      } else {
        layers.forEach(l => {
          if (l.visible) l.wavesurfer.pause();
        });
        isPlaying = false;
      }
    };

    document.getElementById("saveBtn").onclick = () => {
      const exportData = layers.map(l => ({
        id: l.id,
        visible: l.visible,
        volume: l.volume
      }));

      fetch("/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project: currentProject, settings: exportData })
      }).then(res => res.blob())
        .then(blob => {
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = currentProject + ".wave";
          a.click();
        });
    };

    document.getElementById("openBtn").onclick = () => {
      let name = prompt("Enter project name:");
      if (name && !projects[name]) {
        projects[name] = [];
        currentProject = name;
        layers = [];
        refreshProjects();
        renderLayers();
      }
    };

    // Downloads area
    function allowDrop(ev) {
      ev.preventDefault();
    }

    document.getElementById("downloads").ondrop = ev => {
      ev.preventDefault();
      if (ev.dataTransfer.files.length > 0) {
        const file = ev.dataTransfer.files[0];
        const url = URL.createObjectURL(file);
        const item = document.createElement("div");
        item.textContent = file.name;
        item.className = "download-item";
        item.draggable = true;
        item.dataset.url = url;
        document.getElementById("downloads").appendChild(item);
      }
    };

    function dropToLayers(ev) {
      ev.preventDefault();
      const url = ev.dataTransfer.getData("url");
      if (url) {
        addLayerFromUrl(url);
      }
    }

    function dropDownload(ev) {
      ev.preventDefault();
    }

    document.addEventListener("dragstart", ev => {
      if (ev.target.classList.contains("download-item")) {
        ev.dataTransfer.setData("url", ev.target.dataset.url);
      }
    });

    function addLayerFromUrl(url) {
      if (layers.length >= 5) return;
      const layer = { id: layerId++, url, visible: true, volume: 1 };
      layers.push(layer);
      projects[currentProject] = layers;
      renderLayers();
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(html)

@app.route("/upload", methods=["POST"])
def upload():
    global projects
    data = request.json
    audio_b64 = data["audio"]
    layer_id = data["id"]
    project = data["project"]

    header, encoded = audio_b64.split(",", 1)
    audio_bytes = base64.b64decode(encoded)

    if project not in projects:
        projects[project] = []
    projects[project].append({"id": layer_id, "audio": AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")})
    return "ok"

@app.route("/save", methods=["POST"])
def save():
    global projects
    data = request.json
    project = data["project"]
    settings = data["settings"]

    layers = projects.get(project, [])
    mix = None
    for setting in settings:
        layer = next((l for l in layers if l["id"] == setting["id"]), None)
        if not layer:
            continue
        if not setting["visible"]:
            continue

        gain = 20 * (float(setting["volume"]) - 1)
        adjusted = layer["audio"].apply_gain(gain)

        if mix is None:
            mix = adjusted
        else:
            mix = mix.overlay(adjusted)

    if mix is None:
        return "No layers selected!", 400

    buf = io.BytesIO()
    mix.export(buf, format="wav")
    buf.seek(0)
    return send_file(buf, mimetype="audio/wav", as_attachment=True, download_name=f"{project}.wave")

if __name__ == "__main__":
    app.run(debug=True)
