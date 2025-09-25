from flask import Flask, send_file
from io import BytesIO
from pydub import AudioSegment

app = Flask(__name__)

@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html>
<head>
  <title>Bob Wave 🎤</title>
  <style>
    body { font-family: sans-serif; background: #1e1e1e; color: white; text-align: center; }
    button { margin: 5px; padding: 8px 16px; font-size: 14px; cursor: pointer; }
    .track { border: 1px solid #555; margin: 10px; padding: 5px; background: #2a2a2a; }
    .controls { margin-bottom: 5px; }
    #timeline { border: 2px solid #888; height: 200px; margin: 10px; position: relative; background: #111; }
    .clip { position: absolute; height: 40px; background: #4caf50; border-radius: 4px; color: black; font-size: 12px; overflow: hidden; white-space: nowrap; }
  </style>
</head>
<body>
  <h1>Bob Wave 🎶</h1>
  <button onclick="addTrack()">➕ Add Track</button>
  <button onclick="exportMix()">⬇ Export Mix (WAV)</button>
  <div id="tracks"></div>
  <div id="timeline"></div>

<script>
let tracks = [];
let currentStream;
let mediaRecorder;
let chunks = [];
let trackCount = 0;
let clips = [];

function addTrack() {
  const id = trackCount++;
  const trackDiv = document.createElement("div");
  trackDiv.className = "track";
  trackDiv.innerHTML = `
    <div class="controls">
      <button onclick="startRecording(${id})">🎙 Record</button>
      <button onclick="stopRecording(${id})">⏹ Stop</button>
      <button onclick="toggleMute(${id})" id="mute-${id}">🔊 Mute</button>
      Volume: <input type="range" id="vol-${id}" min="0" max="1" step="0.1" value="1">
    </div>
    <div id="clips-${id}"></div>
  `;
  document.getElementById("tracks").appendChild(trackDiv);
  tracks.push({id, muted:false, volume:1, clips:[]});
}

async function startRecording(trackId) {
  currentStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(currentStream);
  chunks = [];
  mediaRecorder.ondataavailable = e => chunks.push(e.data);
  mediaRecorder.onstop = () => {
    const blob = new Blob(chunks, {type: 'audio/webm'});
    const url = URL.createObjectURL(blob);
    const clipId = clips.length;
    clips.push({trackId, url, blob, start: Math.random()*200}); // random pos for now
    renderClips();
  };
  mediaRecorder.start();
}

function stopRecording() {
  if (mediaRecorder) {
    mediaRecorder.stop();
    currentStream.getTracks().forEach(t => t.stop());
  }
}

function renderClips() {
  document.querySelectorAll(".clip").forEach(c => c.remove());
  clips.forEach((clip,i)=>{
    const div = document.createElement("div");
    div.className = "clip";
    div.style.left = clip.start + "px";
    div.style.top = (clip.trackId*50) + "px";
    div.style.width = "100px";
    div.textContent = "Clip " + i;
    document.getElementById("timeline").appendChild(div);
  });
}

function toggleMute(id) {
  const track = tracks.find(t=>t.id===id);
  track.muted = !track.muted;
  document.getElementById("mute-"+id).textContent = track.muted ? "🔇 Unmute" : "🔊 Mute";
}

function exportMix() {
  const formData = new FormData();
  clips.forEach((clip,i)=>{
    formData.append("clip"+i, clip.blob, "clip"+i+".webm");
    formData.append("track"+i, clip.trackId);
    formData.append("vol"+i, document.getElementById("vol-"+clip.trackId).value);
    formData.append("mute"+i, tracks.find(t=>t.id===clip.trackId).muted);
  });
  fetch("/export", {method:"POST", body: formData})
    .then(r=>r.blob())
    .then(blob=>{
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "bob_mix.wav";
      a.click();
    });
}
</script>
</body>
</html>
    """

@app.route("/export", methods=["POST"])
def export():
    from flask import request
    files = request.files
    form = request.form
    mix = AudioSegment.silent(duration=1000)

    for i, f in enumerate(files.values()):
        blob = BytesIO(f.read())
        seg = AudioSegment.from_file(blob, format="webm")
        track_id = int(form.get(f"track{i}", 0))
        vol = float(form.get(f"vol{i}", 1.0))
        muted = form.get(f"mute{i}", "false") == "true"
        if not muted:
            seg = seg + (20 * (vol-1))  # adjust volume
            mix = mix.overlay(seg)

    buf = BytesIO()
    mix.export(buf, format="wav")
    buf.seek(0)
    return send_file(buf, mimetype="audio/wav", as_attachment=True, download_name="bob_mix.wav")

if __name__ == "__main__":
    app.run(debug=True)
