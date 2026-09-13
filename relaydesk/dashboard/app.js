const state = {
  workflows: [],
  selected: null,
  originalDraft: "",
};

const els = {
  queueList: document.querySelector("#queue-list"),
  queueCount: document.querySelector("#queue-count"),
  queueSync: document.querySelector("#queue-sync"),
  refresh: document.querySelector("#refresh-button"),
  reviewerId: document.querySelector("#reviewer-id"),
  empty: document.querySelector("#empty-state"),
  content: document.querySelector("#review-content"),
  priority: document.querySelector("#priority-pill"),
  category: document.querySelector("#category-pill"),
  ticketId: document.querySelector("#ticket-id"),
  intent: document.querySelector("#intent-summary"),
  routeReason: document.querySelector("#route-reason"),
  confidence: document.querySelector("#confidence-value"),
  customerMessage: document.querySelector("#customer-message"),
  receivedAt: document.querySelector("#received-at"),
  customerMeta: document.querySelector("#customer-meta"),
  sentiment: document.querySelector("#sentiment-pill"),
  classificationCategory: document.querySelector("#classification-category"),
  classificationPriority: document.querySelector("#classification-priority"),
  modelRoute: document.querySelector("#model-route"),
  finalRoute: document.querySelector("#final-route"),
  rationale: document.querySelector("#rationale-summary"),
  riskFlags: document.querySelector("#risk-flags"),
  sourceCount: document.querySelector("#source-count"),
  sourceList: document.querySelector("#source-list"),
  draftFlags: document.querySelector("#draft-flags"),
  draftText: document.querySelector("#draft-text"),
  auditList: document.querySelector("#audit-list"),
  reviewNotes: document.querySelector("#review-notes"),
  toast: document.querySelector("#toast"),
  actions: [...document.querySelectorAll("[data-action]")],
};

function humanize(value = "") {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function showToast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle("error", isError);
  els.toast.classList.add("visible");
  window.setTimeout(() => els.toast.classList.remove("visible"), 3200);
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === "string"
      ? payload.detail
      : payload.detail?.message || `Request failed (${response.status})`;
    throw new Error(detail);
  }
  return payload;
}

function renderQueue() {
  els.queueCount.textContent = state.workflows.length;
  els.queueList.innerHTML = "";

  if (!state.workflows.length) {
    els.queueList.innerHTML = `
      <div class="queue-item">
        <strong>Queue clear</strong>
        <p>No RelayDesk workflows currently require human review.</p>
        <div class="queue-item-bottom"><span>Safe to step away</span></div>
      </div>`;
    return;
  }

  for (const workflow of state.workflows) {
    const button = document.createElement("button");
    button.className = `queue-item${state.selected?.workflow_id === workflow.workflow_id ? " active" : ""}`;
    button.type = "button";
    const classification = workflow.classification || {};
    const riskCount = (classification.risk_flags || []).filter((flag) => flag !== "none").length;
    button.innerHTML = `
      <div class="queue-item-top">
        <strong>${humanize(classification.priority || "normal")} priority</strong>
        <span class="pill secondary">${Math.round((classification.confidence || 0) * 100)}%</span>
      </div>
      <p>${classification.intent_summary || workflow.ticket.customer_message}</p>
      <div class="queue-item-bottom">
        <span>${humanize(classification.category || "unclassified")}</span>
        <span>${riskCount ? `${riskCount} risk flag${riskCount === 1 ? "" : "s"}` : "No risk flags"}</span>
      </div>`;
    button.addEventListener("click", () => selectWorkflow(workflow.workflow_id));
    els.queueList.append(button);
  }
}

async function loadQueue({ preserveSelection = true } = {}) {
  const previous = preserveSelection ? state.selected?.workflow_id : null;
  try {
    const workflows = await api("/api/v1/workflows?status=awaiting_review&limit=100");
    state.workflows = workflows;
    els.queueSync.textContent = `Synced ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;

    const nextId = previous && workflows.some((item) => item.workflow_id === previous)
      ? previous
      : workflows[0]?.workflow_id;

    if (nextId) {
      await selectWorkflow(nextId, false);
    } else {
      state.selected = null;
      els.empty.classList.remove("hidden");
      els.content.classList.add("hidden");
      renderQueue();
    }
  } catch (error) {
    els.queueSync.textContent = "Sync failed";
    showToast(error.message, true);
  }
}

async function selectWorkflow(workflowId, rerenderQueue = true) {
  try {
    const [workflow, audit] = await Promise.all([
      api(`/api/v1/workflows/${workflowId}`),
      api(`/api/v1/workflows/${workflowId}/audit`),
    ]);
    workflow.audit = audit;
    state.selected = workflow;
    state.originalDraft = workflow.draft?.draft_text || "";
    renderDetail();
    if (rerenderQueue) renderQueue();
  } catch (error) {
    showToast(error.message, true);
  }
}

function renderDetail() {
  const workflow = state.selected;
  if (!workflow) return;

  els.empty.classList.add("hidden");
  els.content.classList.remove("hidden");

  const ticket = workflow.ticket || {};
  const classification = workflow.classification || {};
  const routing = workflow.routing || {};
  const draft = workflow.draft || {};
  const sources = workflow.retrieved_sources || [];
  const confidence = Math.round((classification.confidence || 0) * 100);

  els.priority.textContent = humanize(classification.priority || "unknown");
  els.category.textContent = humanize(classification.category || "unknown");
  els.ticketId.textContent = ticket.ticket_id || "";
  els.intent.textContent = classification.intent_summary || "Review required";
  els.routeReason.textContent = routing.reason || "RelayDesk routed this ticket for human judgment.";
  els.confidence.textContent = `${confidence}%`;
  els.confidence.parentElement.style.setProperty("--confidence", `${confidence}%`);
  els.customerMessage.textContent = ticket.customer_message || "";
  els.receivedAt.textContent = formatTime(ticket.received_at);
  els.sentiment.textContent = humanize(classification.sentiment || "unknown");
  els.classificationCategory.textContent = humanize(classification.category || "unknown");
  els.classificationPriority.textContent = humanize(classification.priority || "unknown");
  els.modelRoute.textContent = humanize(classification.recommended_route || "unknown");
  els.finalRoute.textContent = humanize(routing.route || "unknown");
  els.rationale.textContent = classification.rationale_summary || "No rationale supplied.";

  const customerMeta = [
    ["Customer", ticket.customer_name || ticket.customer_id || "Unknown"],
    ["Account tier", ticket.account_tier || "Not provided"],
    ["Prior tickets", ticket.prior_ticket_count ?? "Not provided"],
    ["Source", humanize(ticket.source || "unknown")],
  ];
  els.customerMeta.innerHTML = customerMeta.map(([label, value]) => `
    <div class="meta-item"><span>${label}</span><strong>${value}</strong></div>`).join("");

  const risks = classification.risk_flags || ["none"];
  els.riskFlags.innerHTML = risks.map((risk) =>
    `<span class="risk-chip${risk === "none" ? " safe" : ""}">${humanize(risk)}</span>`
  ).join("");

  els.sourceCount.textContent = sources.length;
  els.sourceList.innerHTML = sources.length
    ? sources.map((source) => `
      <div class="source-item">
        <div class="source-title-row">
          <h4>${source.title}</h4>
          <span class="source-score">${Math.round((source.relevance_score || 0) * 100)}%</span>
        </div>
        <p>${source.excerpt}</p>
      </div>`).join("")
    : '<div class="source-item"><h4>No source retrieved</h4><p>This response needs extra scrutiny because no knowledge evidence was attached.</p></div>';

  const flags = [];
  if (draft.requires_account_action) flags.push('<span class="draft-chip">Account action required</span>');
  if (draft.unsupported_action_claimed) flags.push('<span class="draft-chip danger">Unsupported action flagged</span>');
  if (!flags.length) flags.push('<span class="draft-chip">Grounded draft</span>');
  els.draftFlags.innerHTML = flags.join("");
  els.draftText.value = draft.draft_text || "";
  els.reviewNotes.value = "";

  const audit = workflow.audit || [];
  els.auditList.innerHTML = audit.length
    ? audit.map((event) => `
      <li class="audit-item">
        <span class="audit-dot" aria-hidden="true"></span>
        <div>
          <strong>${humanize(event.event_type)}</strong>
          <p>${auditDescription(event)}</p>
        </div>
        <time class="audit-time">${formatTime(event.occurred_at)}</time>
      </li>`).join("")
    : '<li class="audit-item"><span class="audit-dot"></span><div><strong>No audit events</strong></div></li>';
}

function auditDescription(event) {
  const details = event.details || {};
  if (event.event_type === "ticket_classified") {
    return `${humanize(details.category || "unknown")} · ${Math.round((details.confidence || 0) * 100)}% confidence`;
  }
  if (event.event_type === "knowledge_retrieved") {
    return `${(details.source_ids || []).length} source${(details.source_ids || []).length === 1 ? "" : "s"} retrieved`;
  }
  if (event.event_type === "workflow_completed") {
    return `Routed to ${humanize(details.route || "unknown")}`;
  }
  if (event.event_type === "human_review_decided") {
    return `${humanize(details.action || "reviewed")} by ${details.reviewer_id || "reviewer"}`;
  }
  return event.provider ? `${event.provider}${event.model ? ` · ${event.model}` : ""}` : "Workflow event recorded";
}

async function submitDecision(action) {
  if (!state.selected) return;
  const reviewerId = els.reviewerId.value.trim();
  if (!reviewerId) {
    showToast("Enter a reviewer ID before submitting a decision.", true);
    els.reviewerId.focus();
    return;
  }

  const edited = els.draftText.value.trim();
  if (action === "edit_and_approve" && !edited) {
    showToast("The edited response cannot be blank.", true);
    els.draftText.focus();
    return;
  }

  const payload = {
    ticket_id: state.selected.ticket.ticket_id,
    action,
    reviewer_id: reviewerId,
    reviewed_at: new Date().toISOString(),
    notes: els.reviewNotes.value.trim() || null,
    edited_response: action === "edit_and_approve" ? edited : null,
  };

  setBusy(true);
  try {
    const result = await api(`/api/v1/workflows/${state.selected.workflow_id}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    window.localStorage.setItem("relaydesk-reviewer-id", reviewerId);
    showToast(`${humanize(action)} recorded. Workflow is now ${humanize(result.status)}.`);
    await loadQueue({ preserveSelection: false });
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setBusy(false);
  }
}

function setBusy(busy) {
  els.actions.forEach((button) => {
    button.disabled = busy;
  });
  els.refresh.disabled = busy;
}

els.refresh.addEventListener("click", () => loadQueue());
els.reviewerId.addEventListener("change", () => {
  window.localStorage.setItem("relaydesk-reviewer-id", els.reviewerId.value.trim());
});
els.actions.forEach((button) => {
  button.addEventListener("click", () => submitDecision(button.dataset.action));
});

const savedReviewer = window.localStorage.getItem("relaydesk-reviewer-id");
if (savedReviewer) els.reviewerId.value = savedReviewer;

loadQueue({ preserveSelection: false });
