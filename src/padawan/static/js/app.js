function currentEditorCode() {
  const editor = document.querySelector("[data-editor]");
  return editor ? editor.value : "";
}

function setTerminal(text) {
  const terminal = document.querySelector("[data-terminal]");
  if (terminal) terminal.textContent = text || "No output.";
}

function setRunStatus(status, messages) {
  const label = document.querySelector("[data-run-status]");
  if (label) {
    label.textContent = status || "idle";
    label.className = "pill status-" + (status || "not-started");
  }
  const list = document.querySelector("[data-run-messages]");
  if (list) {
    list.innerHTML = "";
    (messages || []).forEach((message) => {
      const item = document.createElement("li");
      item.textContent = message;
      list.appendChild(item);
    });
  }
}

async function runLesson(button) {
  const payload = {
    course_id: button.dataset.courseId,
    lesson_id: button.dataset.lessonId,
    runtime: button.dataset.runtime,
    code: currentEditorCode(),
  };
  button.disabled = true;
  setRunStatus("running", ["Running in a temporary workspace."]);
  try {
    const response = await fetch("/runtime/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    const output = [
      "$ padawan runtime",
      "",
      "stdout:",
      result.stdout || "",
      "",
      "stderr:",
      result.stderr || "",
      "",
      "exit_code: " + (result.exit_code ?? "n/a"),
    ].join("\n");
    setTerminal(output);
    setRunStatus(result.status, result.messages);
  } catch (error) {
    setTerminal(String(error));
    setRunStatus("error", ["Runtime request failed."]);
  } finally {
    button.disabled = false;
  }
}

async function askCodex(button) {
  const dialog = document.querySelector("#codex-dialog");
  const output = document.querySelector("[data-codex-output]");
  if (dialog) dialog.showModal();
  if (dialog) dialog.dataset.threadId = "";
  if (output) output.textContent = "Asking Codex...";
  const payload = {
    course_id: button.dataset.courseId,
    lesson_id: button.dataset.lessonId,
    code: currentEditorCode(),
  };
  try {
    const response = await fetch("/codex/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (output) output.textContent = result.final_message || result.error || "No Codex output.";
    if (dialog && result.thread_id) dialog.dataset.threadId = result.thread_id;
  } catch (error) {
    if (output) output.textContent = String(error);
  }
}

async function continueCodexChat(form) {
  const dialog = document.querySelector("#codex-dialog");
  const output = document.querySelector("[data-codex-output]");
  const threadId = dialog ? dialog.dataset.threadId : "";
  const input = form.querySelector("textarea[name='message']");
  const message = input ? input.value.trim() : "";
  if (!threadId || !message) return;
  if (output) output.textContent += "\n\nYou: " + message + "\n\nCodex: ...";
  try {
    const response = await fetch("/codex/chat/" + encodeURIComponent(threadId), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const result = await response.json();
    if (output) {
      output.textContent = output.textContent.replace(
        /\n\nCodex: \.\.\.$/,
        "\n\nCodex: " + (result.final_message || result.error || "No Codex output."),
      );
    }
    if (input) input.value = "";
  } catch (error) {
    if (output) output.textContent += "\n\n" + String(error);
  }
}

function renderDraftValidationStatus(courseId, validation) {
  const panel = document.getElementById("draft-status-" + courseId);
  if (!panel) return;
  const status = validation?.status || "not-started";
  const summary = validation?.summary || "Waiting for validation status.";
  const created = validation?.created_at ? "Recorded " + validation.created_at : "";
  const statusLine = document.createElement("p");
  statusLine.className = "pill status-" + status;
  statusLine.textContent = "Validation: " + status;
  const summaryLine = document.createElement("p");
  summaryLine.className = "muted";
  summaryLine.textContent = summary;
  const children = [statusLine, summaryLine];
  if (created) {
    const createdLine = document.createElement("p");
    createdLine.className = "muted";
    createdLine.textContent = created;
    children.push(createdLine);
  }
  panel.replaceChildren(...children);
}

function validationFinished(status) {
  return !["queued", "running"].includes(status || "");
}

async function pollDraftValidation(courseId, runId) {
  try {
    const response = await fetch("/validations/" + encodeURIComponent(runId));
    const result = await response.json();
    if (!result.ok) {
      renderDraftValidationStatus(courseId, { status: "error", summary: result.error });
      return;
    }
    renderDraftValidationStatus(courseId, result.validation);
    if (!validationFinished(result.validation.status)) {
      window.setTimeout(() => pollDraftValidation(courseId, runId), 1000);
    }
  } catch (error) {
    renderDraftValidationStatus(courseId, { status: "error", summary: String(error) });
  }
}

async function startDraftValidation(form) {
  const courseId = form.dataset.courseId;
  const button = form.querySelector("button[type='submit']");
  if (button) button.disabled = true;
  renderDraftValidationStatus(courseId, {
    status: "queued",
    summary: "Queued for validation.",
  });
  try {
    const response = await fetch(form.action.replace(/\/validate$/, "/validate/start"), {
      method: "POST",
    });
    const result = await response.json();
    if (!result.ok) {
      renderDraftValidationStatus(courseId, { status: "error", summary: result.error });
      return;
    }
    renderDraftValidationStatus(courseId, result.validation);
    await pollDraftValidation(courseId, result.run_id);
  } catch (error) {
    renderDraftValidationStatus(courseId, { status: "error", summary: String(error) });
  } finally {
    if (button) button.disabled = false;
  }
}

const peerState = {
  identity: null,
  session: null,
  token: "",
  socket: null,
  connection: null,
  dataChannel: null,
  initiator: false,
};

function peerRoot() {
  return document.querySelector("[data-peer-app]");
}

function setPeerStatus(text) {
  const status = document.querySelector("[data-peer-status]");
  if (status) status.textContent = text;
}

function setPeerDataStatus(text) {
  const status = document.querySelector("[data-peer-data-status]");
  if (status) status.textContent = text;
}

function peerFormValue(selector) {
  const input = document.querySelector(selector);
  return input ? input.value.trim() : "";
}

function appendPeerLog(text) {
  const log = document.querySelector("[data-peer-chat-log]");
  if (!log) return;
  const line = document.createElement("p");
  line.textContent = text;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function renderPeerRoster(participants) {
  const roster = document.querySelector("[data-peer-roster]");
  if (!roster) return;
  roster.innerHTML = "";
  (participants || []).forEach((participant) => {
    const item = document.createElement("p");
    item.className = "pill";
    item.textContent = participant.username + " (" + participant.role + ") #" + participant.suffix;
    roster.appendChild(item);
  });
}

async function peerJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok || result.ok === false) {
    throw new Error(result.error || result.detail || "Peer request failed.");
  }
  return result;
}

async function createPeerSession() {
  const payload = {
    username: peerFormValue("[data-peer-username]"),
    role: peerFormValue("[data-peer-role]") || "padawan",
    ice_profile: peerFormValue("[data-peer-ice-profile]") || "local-turn",
  };
  const result = await peerJson("/peer/sessions", payload);
  peerState.identity = result.identity;
  peerState.session = result.session;
  peerState.token = result.token;
  const token = document.querySelector("[data-peer-token]");
  if (token) token.value = result.token;
  renderPeerRoster(result.session.participants);
  await connectPeerSocket(true);
  setPeerStatus("Session token created.");
}

async function joinPeerSession() {
  const token = peerFormValue("[data-peer-token]");
  const payload = {
    token,
    username: peerFormValue("[data-peer-username]"),
    role: peerFormValue("[data-peer-role]") || "padawan",
  };
  const result = await peerJson("/peer/sessions/join", payload);
  peerState.identity = result.identity;
  peerState.session = result.session;
  peerState.token = token;
  renderPeerRoster(result.session.participants);
  await connectPeerSocket(false);
  setPeerStatus("Joined peer session.");
}

async function connectPeerSocket(initiator) {
  await ensurePeerConnection(initiator);
  peerState.initiator = initiator;
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  const sessionId = encodeURIComponent(peerState.session.session_id);
  const token = encodeURIComponent(peerState.token);
  const peerId = encodeURIComponent(peerState.identity.peer_id);
  peerState.socket = new WebSocket(`${scheme}://${window.location.host}/peer/ws/${sessionId}?token=${token}&peer_id=${peerId}`);
  peerState.socket.addEventListener("open", async () => {
    setPeerStatus("Signaling connected.");
    if (initiator) await sendPeerOffer();
  });
  peerState.socket.addEventListener("message", (event) => {
    handlePeerSignal(JSON.parse(event.data)).catch((error) => setPeerStatus(String(error)));
  });
  peerState.socket.addEventListener("close", () => setPeerStatus("Signaling disconnected."));
}

async function ensurePeerConnection(initiator) {
  if (peerState.connection) return;
  const profile = peerFormValue("[data-peer-ice-profile]") || "local-turn";
  const iceResponse = await fetch("/peer/ice-config?profile=" + encodeURIComponent(profile));
  const iceConfig = await iceResponse.json();
  const connection = new RTCPeerConnection({ iceServers: iceConfig.ice_servers || [] });
  peerState.connection = connection;
  connection.addEventListener("icecandidate", (event) => {
    if (event.candidate && peerState.socket?.readyState === WebSocket.OPEN) {
      peerState.socket.send(JSON.stringify({ type: "candidate", candidate: event.candidate }));
    }
  });
  connection.addEventListener("track", (event) => {
    const video = document.querySelector("[data-peer-remote-video]");
    if (video && event.streams[0]) video.srcObject = event.streams[0];
  });
  connection.addEventListener("datachannel", (event) => configureDataChannel(event.channel));
  if (initiator) configureDataChannel(connection.createDataChannel("padawan-peer"));
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
    const local = document.querySelector("[data-peer-local-video]");
    if (local) local.srcObject = stream;
    stream.getTracks().forEach((track) => connection.addTrack(track, stream));
  } catch (error) {
    appendPeerLog("Media unavailable: " + String(error));
  }
}

function configureDataChannel(channel) {
  peerState.dataChannel = channel;
  channel.addEventListener("open", () => setPeerDataStatus("Open."));
  channel.addEventListener("close", () => setPeerDataStatus("Closed."));
  channel.addEventListener("message", (event) => handlePeerData(JSON.parse(event.data)));
}

async function sendPeerOffer() {
  if (!peerState.connection || peerState.socket?.readyState !== WebSocket.OPEN) return;
  if (peerState.connection.localDescription?.type === "offer") {
    peerState.socket.send(JSON.stringify({ type: "offer", description: peerState.connection.localDescription }));
    return;
  }
  if (peerState.connection.signalingState !== "stable") return;
  const offer = await peerState.connection.createOffer();
  await peerState.connection.setLocalDescription(offer);
  peerState.socket.send(JSON.stringify({ type: "offer", description: offer }));
}

async function handlePeerSignal(message) {
  if (message.type === "peer-joined") {
    renderPeerRoster(message.participants);
    if (peerState.initiator) await sendPeerOffer();
    return;
  }
  await ensurePeerConnection(false);
  if (message.type === "offer") {
    await peerState.connection.setRemoteDescription(message.description);
    const answer = await peerState.connection.createAnswer();
    await peerState.connection.setLocalDescription(answer);
    peerState.socket.send(JSON.stringify({ type: "answer", description: answer }));
    return;
  }
  if (message.type === "answer") {
    await peerState.connection.setRemoteDescription(message.description);
    return;
  }
  if (message.type === "candidate") {
    await peerState.connection.addIceCandidate(message.candidate);
  }
}

function sendPeerData(payload) {
  if (!peerState.dataChannel || peerState.dataChannel.readyState !== "open") {
    throw new Error("Data channel is not open.");
  }
  peerState.dataChannel.send(JSON.stringify({ from: peerState.identity.peer_id, ...payload }));
}

function handlePeerData(message) {
  if (message.type === "chat") {
    appendPeerLog("Peer: " + message.text);
    return;
  }
  if (message.type === "course") {
    peerJson("/peer/courses", { peer_id: message.from, course: message.course })
      .then((result) => appendPeerLog("Received course: " + result.course_id))
      .catch((error) => appendPeerLog(String(error)));
    return;
  }
  if (message.type === "progress") {
    peerJson("/peer/progress", {
      peer_id: message.from,
      course_id: message.course_id,
      progress: message.progress,
    })
      .then(() => appendPeerLog("Received progress: " + message.course_id))
      .catch((error) => appendPeerLog(String(error)));
  }
}

async function sendPeerChat(form) {
  const input = form.querySelector("[data-peer-chat-input]");
  const text = input ? input.value.trim() : "";
  if (!text) return;
  sendPeerData({ type: "chat", text });
  appendPeerLog("You: " + text);
  if (input) input.value = "";
}

async function sendPeerCourse() {
  const courseId = peerFormValue("[data-peer-course-select]");
  const response = await fetch("/peer/courses/" + encodeURIComponent(courseId) + "/export");
  const result = await response.json();
  if (!result.ok) throw new Error(result.error || "Course export failed.");
  sendPeerData({ type: "course", course: result.course });
  appendPeerLog("Sent course: " + courseId);
}

async function sendPeerProgress() {
  const courseId = peerFormValue("[data-peer-progress-select]");
  const response = await fetch("/peer/progress/" + encodeURIComponent(courseId));
  const result = await response.json();
  if (!result.ok) throw new Error(result.error || "Progress export failed.");
  sendPeerData({ type: "progress", course_id: courseId, progress: result.progress });
  appendPeerLog("Sent progress: " + courseId);
}

function wirePeerApp() {
  if (!peerRoot()) return;
  const create = document.querySelector("[data-peer-create]");
  const join = document.querySelector("[data-peer-join]");
  const course = document.querySelector("[data-peer-send-course]");
  const progress = document.querySelector("[data-peer-send-progress]");
  if (create) create.addEventListener("click", () => createPeerSession().catch((error) => setPeerStatus(String(error))));
  if (join) join.addEventListener("click", () => joinPeerSession().catch((error) => setPeerStatus(String(error))));
  if (course) course.addEventListener("click", () => sendPeerCourse().catch((error) => setPeerStatus(String(error))));
  if (progress) progress.addEventListener("click", () => sendPeerProgress().catch((error) => setPeerStatus(String(error))));
}

document.addEventListener("click", (event) => {
  const run = event.target.closest("[data-run-lesson]");
  if (run) runLesson(run);
  const codex = event.target.closest("[data-ask-codex]");
  if (codex) askCodex(codex);
});

document.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-codex-chat-form]");
  if (form) {
    event.preventDefault();
    continueCodexChat(form);
    return;
  }
  const validationForm = event.target.closest("[data-validate-draft]");
  const peerChatForm = event.target.closest("[data-peer-chat-form]");
  if (peerChatForm) {
    event.preventDefault();
    sendPeerChat(peerChatForm).catch((error) => setPeerStatus(String(error)));
    return;
  }
  if (!validationForm) return;
  event.preventDefault();
  startDraftValidation(validationForm);
});

document.addEventListener("DOMContentLoaded", wirePeerApp);
