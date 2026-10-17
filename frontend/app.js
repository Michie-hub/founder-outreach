const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const statusLabels = {
  not_contacted: "Not contacted",
  contacted: "Contacted",
  replied: "Replied",
  not_interested: "Not interested",
  meeting_booked: "Meeting booked",
};

let currentSearchCandidates = [];

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const temporaryField = document.createElement("textarea");
  temporaryField.value = text;
  temporaryField.style.position = "fixed";
  temporaryField.style.opacity = "0";
  document.body.appendChild(temporaryField);
  temporaryField.select();
  const copied = document.execCommand("copy");
  temporaryField.remove();
  if (!copied) throw new Error("Clipboard access is unavailable in this browser.");
}

async function readApiResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  let payload;
  if (contentType.includes("application/json")) {
    try {
      payload = await response.json();
    } catch {
      throw new Error(`The server returned invalid JSON (${response.status}).`);
    }
  } else {
    const text = await response.text();
    if (!response.ok) {
      throw new Error(`Server error (${response.status}): ${text.slice(0, 180)}`);
    }
    throw new Error("The server returned an unexpected response format.");
  }
  if (!response.ok) {
    const detail = payload.detail || payload.message || `Request failed (${response.status}).`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload;
}

function showApiState(connected) {
  $("#api-dot").classList.toggle("connected", connected);
  $("#api-label").textContent = connected ? "API connected" : "API unavailable";
}

function setFlowState(step, state) {
  const flowSteps = $$(".flow-step");
  const connectors = $$(".flow-connector");
  const index = flowSteps.findIndex((element) => element.dataset.step === step);
  flowSteps.forEach((element, i) => {
    element.classList.toggle("active", i === index && state === "active");
    if (i < index || (i === index && state === "complete")) {
      element.classList.add("complete");
    } else {
      element.classList.remove("complete");
    }
  });
  connectors.forEach((element, i) => element.classList.toggle("complete", i < index || (i === index && state === "complete")));
}

function resetFlow() {
  $$(".flow-step").forEach((element) => element.classList.remove("active", "complete"));
  $$(".flow-connector").forEach((element) => element.classList.remove("complete"));
  $("#trace-label").textContent = "SEARCH IN PROGRESS";
  $("#trace-detail").textContent = "Sending your search criteria to the founder discovery service…";
  setFlowState("search", "active");
}

const pause = (duration) => new Promise((resolve) => window.setTimeout(resolve, duration));

async function animateExecution(events = []) {
  for (const event of events) {
    setFlowState(event.step, "active");
    $("#trace-detail").textContent = event.detail;
    await pause(420);
    setFlowState(event.step, "complete");
  }
  $("#trace-label").textContent = events.length ? "SEARCH COMPLETE" : "NO EXECUTION TRACE";
  if (events.length) $("#trace-detail").textContent = "Discovery complete. Open a profile, review the evidence, and decide what happens next.";
}

function initials(name, company) {
  const source = name || company || "?";
  return source.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function renderProspects(founders) {
  const filter = $("#review-filter").value;
  const visible = founders;
  $("#prospect-count").textContent = String(visible.length);
  $("#welcome-count").textContent = String(founders.length);
  $("#nav-count").textContent = String(founders.length);
  const list = $("#prospect-list");

  if (!visible.length) {
    list.innerHTML = `<div class="empty-state"><div class="empty-illustration">✳</div><b>${filter === "all" ? "Your orbit is quiet for now" : `No ${escapeHtml(filter.replaceAll("_", " "))} prospects`}</b><span>${filter === "all" ? "Run a search to bring founder prospects into view." : "Try another review filter or update a prospect's status."}</span></div>`;
    return;
  }

  list.innerHTML = visible.map((founder) => {
    const id = founder.id || "";
    const name = founder.name || "Name not identified";
    const company = founder.company || "Company not identified";
    const role = founder.role || "Role not identified";
    const status = statusLabels[founder.outreach_status] ? founder.outreach_status : "not_contacted";
    const evidence = founder.evidence || "No search snippet was available.";
    const review = founder.review_status || "needs_review";
    const source = escapeHtml(founder.source_url || "");
    return `<article class="prospect-card" data-id="${id}" data-source-url="${escapeHtml(founder.source_url || "")}">
      <div class="prospect-top"><div class="person-avatar">${escapeHtml(initials(founder.name, founder.company))}</div><div class="person-main"><h3>${escapeHtml(name)}</h3><div class="person-line">${escapeHtml(company)} <span class="person-role">${escapeHtml(role)}</span></div></div><span class="review-pill ${escapeHtml(review)}">${escapeHtml(review.replaceAll("_", " ").toUpperCase())}</span></div>
      <p class="evidence">${escapeHtml(evidence)}</p>
      ${source ? `<a class="source-link" href="${source}" target="_blank" rel="noopener noreferrer">Open source page <span>↗</span></a>` : ""}
      <div class="card-controls">
        <div class="review-actions">
          ${review === "needs_review" ? `<button class="small-action approve" data-review="approved" type="button">✓ Approve and save</button><button class="small-action reject" data-review="rejected" type="button">× Reject</button>` : `<span class="review-note">${review === "approved" ? "Approved and saved" : "Rejected for this search"}</span>`}
          <span class="draft-message" aria-live="polite"></span>
        </div>
        ${review === "approved" ? `<div class="outreach-controls">
          <select class="outreach-status" aria-label="Outreach status for ${escapeHtml(name)}">${Object.entries(statusLabels).map(([value, label]) => `<option value="${value}" ${status === value ? "selected" : ""}>${label}</option>`).join("")}</select>
          <textarea class="draft-box" aria-label="Outreach draft for ${escapeHtml(name)}" placeholder="Create or edit a message draft…">${escapeHtml(founder.outreach_draft || "")}</textarea>
          <div class="draft-actions"><button class="small-action generate-draft" type="button">✳ Generate draft</button><button class="copy-draft" type="button">Copy draft</button></div>
        </div>` : ""}
      </div>
    </article>`;
  }).join("");
}

async function loadFounders() {
  if ($("#review-filter").value !== "approved") {
    showApiState(true);
    renderProspects(currentSearchCandidates);
    return;
  }
  try {
    const response = await fetch("/founders");
    if (!response.ok) throw new Error("Could not load founders.");
    const founders = await response.json();
    showApiState(true);
    renderProspects(founders);
  } catch (error) {
    showApiState(false);
    $("#prospect-list").innerHTML = `<div class="empty-state"><div class="empty-illustration">⌁</div><b>Could not connect to the API</b><span>Start the FastAPI server, then refresh this page.</span></div>`;
  }
}

$("#search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const button = $("#search-button");
  const engine = $(".engine-panel");
  const errorBox = $("#search-error");
  const caption = $("#engine-caption");
  let apiResponded = false;
  errorBox.hidden = true;
  button.disabled = true;
  button.querySelector("span:nth-child(2)").textContent = "Searching…";
  engine.classList.remove("done");
  engine.classList.add("running");
  $("#engine-status").textContent = "RUNNING";
  caption.textContent = "Searching public pages for founder signals…";
  resetFlow();

  const payload = {
    country: form.get("country").trim(),
    industry: form.get("industry").trim(),
    role: form.get("role").trim() || "Founder",
    max_results: Number(form.get("max_results")),
  };

  try {
    const response = await fetch("/founders/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    apiResponded = true;
    showApiState(true);
    const data = await readApiResponse(response);
    currentSearchCandidates = data.results.map((founder) => ({
      ...founder,
      id: null,
      review_status: "needs_review",
      outreach_status: "not_contacted",
      outreach_draft: null,
    }));
    $("#review-filter").value = "all";
    caption.textContent = `${data.results.length} complete candidate${data.results.length === 1 ? "" : "s"} ready for your review`;
    await animateExecution(data.execution || []);
    engine.classList.remove("running");
    engine.classList.add("done");
    $("#engine-status").textContent = "COMPLETE";
    await loadFounders();
    $("#prospects").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    engine.classList.remove("running", "done");
    $("#engine-status").textContent = "ERROR";
    caption.textContent = "The search could not be completed";
    $("#trace-label").textContent = "SEARCH FAILED";
    $("#trace-detail").textContent = "No prospects were changed. Check your search settings or try again.";
    errorBox.textContent = error.message;
    errorBox.hidden = false;
    if (!apiResponded) showApiState(false);
  } finally {
    button.disabled = false;
    button.querySelector("span:nth-child(2)").textContent = "Start discovery";
  }
});

$("#prospect-list").addEventListener("click", async (event) => {
  const card = event.target.closest(".prospect-card");
  if (!card) return;
  const message = $(".draft-message", card);
  const id = card.dataset.id;

  if (event.target.matches("[data-review]")) {
    const button = event.target;
    button.disabled = true;
    try {
      const candidate = currentSearchCandidates.find((item) => item.source_url === card.dataset.sourceUrl);
      if (!candidate) throw new Error("This search result has expired. Run the search again to review it.");
      if (button.dataset.review === "approved") {
        const response = await fetch("/founders", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...candidate, review_status: "approved" }),
        });
        const saved = await readApiResponse(response);
        Object.assign(candidate, saved);
      } else {
        candidate.review_status = "rejected";
      }
      await loadFounders();
    } catch (error) {
      message.textContent = error.message;
      button.disabled = false;
    }
  }

  if (event.target.matches(".generate-draft")) {
    const button = event.target;
    button.disabled = true;
    button.textContent = "Writing…";
    try {
      const response = await fetch(`/founders/${id}/outreach-draft`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}),
      });
      const data = await readApiResponse(response);
      $(".draft-box", card).value = data.outreach_draft;
      message.textContent = "Draft saved";
      window.setTimeout(() => { if (message.isConnected) message.textContent = ""; }, 2600);
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
      button.innerHTML = "✳ Generate draft";
    }
  }

  if (event.target.matches(".copy-draft")) {
    const button = event.target;
    const draft = $(".draft-box", card).value.trim();
    if (!draft) {
      message.textContent = "Generate a draft first.";
      return;
    }
    button.disabled = true;
    try {
      await copyTextToClipboard(draft);
      message.textContent = "Copied to clipboard";
      window.setTimeout(() => { if (message.isConnected) message.textContent = ""; }, 2600);
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }
});

$("#prospect-list").addEventListener("change", async (event) => {
  if (!event.target.matches(".outreach-status")) return;
  const card = event.target.closest(".prospect-card");
  const message = $(".draft-message", card);
  try {
    const response = await fetch(`/founders/${card.dataset.id}/outreach`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outreach_status: event.target.value }),
    });
    await readApiResponse(response);
    message.textContent = "Status updated";
    window.setTimeout(() => { if (message.isConnected) message.textContent = ""; }, 2200);
  } catch (error) {
    message.textContent = error.message;
  }
});

$("#review-filter").addEventListener("change", loadFounders);
$("#refresh-button").addEventListener("click", () => {
  if ($("#review-filter").value === "approved") loadFounders();
  else {
    currentSearchCandidates = [];
    renderProspects(currentSearchCandidates);
  }
});

loadFounders();
