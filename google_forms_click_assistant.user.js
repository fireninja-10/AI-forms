// ==UserScript==
// @name         AI Agent Google Forms Click Assistant
// @namespace    https://github.com/
// @version      1.0.0
// @description  Clique sur une question Google Forms pour la faire remplir par l'agent local quand le mode est active.
// @match        https://docs.google.com/forms/*
// @grant        GM_xmlhttpRequest
// @grant        GM_addStyle
// @connect      127.0.0.1
// @connect      localhost
// ==/UserScript==

(function () {
  "use strict";

  const STORAGE_KEY = "ai-agent-google-forms-state";
  const API_URL = "http://127.0.0.1:8000/api/forms/answer";

  const state = {
    enabled: false,
    context: "",
    busy: false,
  };

  function loadState() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      state.enabled = Boolean(saved.enabled);
      state.context = typeof saved.context === "string" ? saved.context : "";
    } catch (_error) {
      state.enabled = false;
      state.context = "";
    }
  }

  function saveState() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ enabled: state.enabled, context: state.context })
    );
  }

  function cleanText(value) {
    return (value || "").replace(/\s+/g, " ").replace(/\*$/, "").trim();
  }

  function unique(items) {
    return [...new Set(items.filter(Boolean))];
  }

  function detectKind(block) {
    if (block.querySelector("textarea")) {
      return "paragraph";
    }
    if (block.querySelector("input[type='text']")) {
      return "short_text";
    }
    if (block.querySelector("[role='radio']")) {
      return "multiple_choice";
    }
    if (block.querySelector("[role='checkbox']")) {
      return "checkboxes";
    }
    if (block.querySelector("[role='listbox'], [role='combobox']")) {
      return "dropdown";
    }
    return "unknown";
  }

  function extractOptions(block) {
    const texts = [];
    block.querySelectorAll("[role='radio'], [role='checkbox'], [role='option'], label").forEach((node) => {
      const text = cleanText(node.textContent || "");
      if (text) {
        texts.push(text);
      }
    });
    return unique(texts);
  }

  function extractQuestion(block) {
    const headingNodes = [...block.querySelectorAll("[role='heading']")];
    const title = cleanText(
      headingNodes.map((node) => node.textContent || "").find((value) => cleanText(value)) ||
        (block.textContent || "").split("\n")[0]
    );

    return {
      title,
      kind: detectKind(block),
      required: (block.textContent || "").includes("*"),
      options: extractOptions(block),
    };
  }

  function setStatus(text, variant = "idle") {
    const status = document.getElementById("ai-agent-status");
    if (!status) {
      return;
    }
    status.textContent = text;
    status.dataset.variant = variant;
  }

  function closestQuestionBlock(target) {
    return target.closest("div[role='listitem']");
  }

  function findClickableByText(block, selector, text) {
    return [...block.querySelectorAll(selector)].find((node) => {
      const nodeText = cleanText(node.textContent || "");
      return nodeText.toLowerCase().includes(String(text).toLowerCase());
    });
  }

  function fillQuestion(block, question, answer) {
    if (!answer) {
      return;
    }

    if (question.kind === "paragraph") {
      const field = block.querySelector("textarea");
      if (field) {
        field.focus();
        field.value = String(answer);
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.dispatchEvent(new Event("change", { bubbles: true }));
      }
      return;
    }

    if (question.kind === "short_text") {
      const field = block.querySelector("input[type='text']");
      if (field) {
        field.focus();
        field.value = String(answer);
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.dispatchEvent(new Event("change", { bubbles: true }));
      }
      return;
    }

    if (question.kind === "multiple_choice") {
      const node = findClickableByText(block, "label, [role='radio']", String(answer));
      if (node) {
        node.click();
      }
      return;
    }

    if (question.kind === "checkboxes") {
      const values = Array.isArray(answer) ? answer : [String(answer)];
      values.forEach((value) => {
        const node = findClickableByText(block, "label, [role='checkbox']", String(value));
        if (node) {
          node.click();
        }
      });
      return;
    }

    if (question.kind === "dropdown") {
      const combobox = block.querySelector("[role='listbox'], [role='combobox']");
      if (!combobox) {
        return;
      }
      combobox.click();
      setTimeout(() => {
        const node = [...document.querySelectorAll("[role='option'], [role='listitem']")].find((item) => {
          const text = cleanText(item.textContent || "");
          return text.toLowerCase().includes(String(answer).toLowerCase());
        });
        if (node) {
          node.click();
        }
      }, 120);
    }
  }

  function requestAnswer(question) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: "POST",
        url: API_URL,
        headers: { "Content-Type": "application/json" },
        data: JSON.stringify({
          question,
          context: state.context,
        }),
        onload: (response) => {
          try {
            const payload = JSON.parse(response.responseText || "{}");
            if (response.status >= 400) {
              reject(new Error(payload.error || "Erreur API"));
              return;
            }
            resolve(payload.answer);
          } catch (error) {
            reject(error);
          }
        },
        onerror: () => {
          reject(new Error("Le serveur local ne repond pas. Lance python3 web_agent.py"));
        },
      });
    });
  }

  async function handleQuestionClick(event) {
    if (!state.enabled || state.busy) {
      return;
    }

    const block = closestQuestionBlock(event.target);
    if (!block) {
      return;
    }

    if (event.target.closest("#ai-agent-forms-box")) {
      return;
    }

    const question = extractQuestion(block);
    if (!question.title) {
      return;
    }

    state.busy = true;
    setStatus("Generation...", "busy");

    try {
      const answer = await requestAnswer(question);
      fillQuestion(block, question, answer);
      setStatus("Question remplie", "success");
    } catch (error) {
      setStatus(error.message || "Erreur", "error");
    } finally {
      state.busy = false;
    }
  }

  function createPanel() {
    GM_addStyle(`
      #ai-agent-forms-box {
        position: fixed;
        top: 16px;
        right: 16px;
        z-index: 999999;
        width: 300px;
        padding: 14px;
        border-radius: 18px;
        background: rgba(45, 45, 45, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.14);
        backdrop-filter: blur(14px);
        color: #fff;
        font: 13px/1.4 Arial, sans-serif;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
      }
      #ai-agent-forms-box * {
        box-sizing: border-box;
      }
      #ai-agent-forms-box .row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }
      #ai-agent-forms-box .title {
        margin: 0;
        font-size: 14px;
        font-weight: 700;
      }
      #ai-agent-forms-box .sub {
        margin: 3px 0 0;
        color: rgba(255, 255, 255, 0.72);
        font-size: 12px;
      }
      #ai-agent-forms-box .switch {
        width: 56px;
        height: 30px;
        padding: 3px;
        border: 0;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.18);
        cursor: pointer;
      }
      #ai-agent-forms-box .switch.active {
        background: rgba(121, 224, 164, 0.35);
      }
      #ai-agent-forms-box .thumb {
        width: 24px;
        height: 24px;
        border-radius: 999px;
        background: #fff;
        transform: translateX(0);
        transition: transform 0.18s ease;
      }
      #ai-agent-forms-box .switch.active .thumb {
        transform: translateX(26px);
      }
      #ai-agent-forms-box textarea {
        width: 100%;
        min-height: 74px;
        margin-top: 12px;
        padding: 10px 12px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.08);
        color: #fff;
        resize: vertical;
      }
      #ai-agent-forms-box .status {
        margin-top: 10px;
        font-size: 12px;
        color: rgba(255, 255, 255, 0.74);
      }
      #ai-agent-forms-box .status[data-variant='success'] {
        color: #8af0ba;
      }
      #ai-agent-forms-box .status[data-variant='error'] {
        color: #ff9a9a;
      }
      #ai-agent-forms-box .status[data-variant='busy'] {
        color: #ffe28a;
      }
    `);

    const panel = document.createElement("div");
    panel.id = "ai-agent-forms-box";
    panel.innerHTML = `
      <div class="row">
        <div>
          <p class="title">AI Agent Forms</p>
          <p class="sub">Clique une question pour la remplir quand le mode est active.</p>
        </div>
        <button class="switch" id="ai-agent-toggle" type="button" aria-label="Activer ou desactiver">
          <span class="thumb"></span>
        </button>
      </div>
      <textarea id="ai-agent-context" placeholder="Contexte utilisateur: profil, preferences, infos a reutiliser..."></textarea>
      <div class="status" id="ai-agent-status" data-variant="idle">Mode inactif</div>
    `;
    document.body.appendChild(panel);

    const toggle = panel.querySelector("#ai-agent-toggle");
    const contextField = panel.querySelector("#ai-agent-context");
    contextField.value = state.context;

    function syncToggle() {
      toggle.classList.toggle("active", state.enabled);
      setStatus(state.enabled ? "Mode actif: clique une question" : "Mode inactif", "idle");
    }

    toggle.addEventListener("click", () => {
      state.enabled = !state.enabled;
      saveState();
      syncToggle();
    });

    contextField.addEventListener("input", () => {
      state.context = contextField.value;
      saveState();
    });

    syncToggle();
  }

  loadState();
  createPanel();
  document.addEventListener("click", handleQuestionClick, true);
})();
