const button = document.getElementById("capture");
const statusNode = document.getElementById("status");

button.addEventListener("click", async () => {
  button.disabled = true;
  setStatus("Capturing page…");
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    if (!tab?.id || /^(chrome|edge|about):/.test(tab.url || "")) throw new Error("Open a normal job webpage first.");
    await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ["content.js"]});
    const extracted = await chrome.tabs.sendMessage(tab.id, {type: "EXTRACT_PAGE"});
    if (!extracted?.ok) throw new Error(extracted?.error || "Page capture failed.");
    const response = await fetch("http://127.0.0.1:8765/api/capture", {
      method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(extracted.page)
    });
    if (!response.ok) throw new Error(`Local queue returned HTTP ${response.status}.`);
    const result = await response.json();
    setStatus(result.duplicate ? "Updated and returned to queue ✓" : "Saved to queue ✓");
    button.textContent = "Captured";
  } catch (error) {
    setStatus(error.message.includes("Failed to fetch") ? "Start the local Job Queue app first." : error.message, true);
    button.disabled = false;
  }
});

function setStatus(message, error=false) { statusNode.textContent = message; statusNode.className = error ? "error" : ""; }
