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

document.addEventListener("click", (event) => {
  const run = event.target.closest("[data-run-lesson]");
  if (run) runLesson(run);
  const codex = event.target.closest("[data-ask-codex]");
  if (codex) askCodex(codex);
});

document.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-codex-chat-form]");
  if (!form) return;
  event.preventDefault();
  continueCodexChat(form);
});
