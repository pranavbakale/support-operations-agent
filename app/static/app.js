const state = {
  accounts: [],
  selectedAccount: null,
  sending: false,
  health: null,
};

const elements = {
  accountSelect: document.querySelector("#account-select"),
  accountSummary: document.querySelector("#account-summary"),
  chatMessages: document.querySelector("#chat-messages"),
  clearChat: document.querySelector("#clear-chat"),
  form: document.querySelector("#message-form"),
  input: document.querySelector("#message-input"),
  sendButton: document.querySelector("#send-button"),
  ticketList: document.querySelector("#ticket-list"),
  ticketCount: document.querySelector("#ticket-count"),
  sidebarStatus: document.querySelector("#sidebar-status"),
  topbarStatus: document.querySelector("#topbar-status"),
  toastRegion: document.querySelector("#toast-region"),
  pageTitle: document.querySelector("#page-title"),
  sidebar: document.querySelector("#sidebar"),
  mobileScrim: document.querySelector("#mobile-scrim"),
};

const welcomeMarkup = elements.chatMessages.innerHTML;

function makeIcon(name, className = "") {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#icon-${name}`);
  svg.setAttribute("aria-hidden", "true");
  if (className) svg.setAttribute("class", className);
  svg.append(use);
  return svg;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // Keep the status-based fallback for non-JSON errors.
    }
    throw new Error(detail);
  }
  return response.json();
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  elements.toastRegion.append(toast);
  window.setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(8px)";
    window.setTimeout(() => toast.remove(), 180);
  }, 3200);
}

function initials(name) {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function titleCase(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function scrollConversation() {
  elements.chatMessages.scrollTo({
    top: elements.chatMessages.scrollHeight,
    behavior: "smooth",
  });
}

function setSending(sending) {
  state.sending = sending;
  elements.sendButton.disabled = sending;
  elements.input.disabled = sending;
}

function resetInputHeight() {
  elements.input.style.height = "auto";
  elements.input.style.height = `${Math.min(elements.input.scrollHeight, 112)}px`;
}

function clearConversation(notify = false) {
  elements.chatMessages.innerHTML = welcomeMarkup;
  if (notify) showToast("Conversation cleared");
}

function buildMessageShell(role) {
  const article = document.createElement("article");
  article.className = `message ${role}-message`;

  const avatar = document.createElement("div");
  avatar.className = `message-avatar ${role === "user" ? "user-avatar" : ""}`;
  avatar.append(makeIcon(role === "user" ? "user" : "spark"));

  const content = document.createElement("div");
  content.className = "message-content";
  article.append(avatar, content);
  return { article, content };
}

function appendUserMessage(text) {
  const { article, content } = buildMessageShell("user");
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  bubble.append(paragraph);
  content.append(bubble);
  elements.chatMessages.append(article);
  scrollConversation();
}

function appendLoadingMessage() {
  const { article, content } = buildMessageShell("assistant");
  article.dataset.loading = "true";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble typing-bubble";
  bubble.setAttribute("aria-label", "Relay is reviewing policy");
  bubble.append(document.createElement("i"), document.createElement("i"), document.createElement("i"));
  content.append(bubble);
  elements.chatMessages.append(article);
  scrollConversation();
  return article;
}

function appendMessageText(bubble, text) {
  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = "Relay assistant";
  bubble.append(label);

  for (const block of text.split(/\n\s*\n/)) {
    const paragraph = document.createElement("p");
    const parts = block.split(/(\[P\d+\])/g);
    for (const part of parts) {
      if (/^\[P\d+\]$/.test(part)) {
        const marker = document.createElement("strong");
        marker.textContent = part;
        marker.style.color = "var(--mint-700)";
        paragraph.append(marker);
      } else {
        paragraph.append(document.createTextNode(part));
      }
    }
    bubble.append(paragraph);
  }
}

function appendCitation(content, citation) {
  const card = document.createElement("div");
  card.className = "citation-card";
  const marker = document.createElement("span");
  marker.className = "citation-marker";
  marker.textContent = citation.marker;
  const copy = document.createElement("div");
  copy.className = "citation-copy";
  const title = document.createElement("strong");
  title.textContent = citation.title;
  const excerpt = document.createElement("span");
  excerpt.textContent = citation.excerpt;
  copy.append(title, excerpt);
  card.append(marker, copy);
  content.append(card);
}

function updateApprovalCard(card, outcome, detail) {
  card.classList.add("resolved", outcome);
  const heading = card.querySelector(".approval-copy strong");
  const message = card.querySelector(".approval-copy span");
  const icon = card.querySelector(".approval-icon");
  icon.replaceChildren(makeIcon(outcome === "approved" ? "check" : "lock"));
  heading.textContent = outcome === "approved" ? "Ticket created" : "Action rejected";
  message.textContent = detail;
}

function appendApproval(content, action) {
  const card = document.createElement("div");
  card.className = "approval-card";

  const header = document.createElement("div");
  header.className = "approval-header";
  const icon = document.createElement("span");
  icon.className = "approval-icon";
  icon.append(makeIcon("ticket"));
  const copy = document.createElement("div");
  copy.className = "approval-copy";
  const title = document.createElement("strong");
  title.textContent = "Approval required";
  const summary = document.createElement("span");
  summary.textContent = action.summary;
  copy.append(title, summary);
  header.append(icon, copy);

  const actions = document.createElement("div");
  actions.className = "approval-actions";
  const approve = document.createElement("button");
  approve.className = "approve-button";
  approve.type = "button";
  approve.textContent = "Approve & create";
  const reject = document.createElement("button");
  reject.className = "reject-button";
  reject.type = "button";
  reject.textContent = "Reject";
  actions.append(approve, reject);
  card.append(header, actions);
  content.append(card);

  approve.addEventListener("click", async () => {
    approve.disabled = true;
    reject.disabled = true;
    approve.textContent = "Creating…";
    try {
      const result = await api(`/v1/approvals/${encodeURIComponent(action.id)}/approve`, {
        method: "POST",
      });
      updateApprovalCard(card, "approved", `Ticket ${result.ticket_id.slice(0, 8)} is now open.`);
      showToast("Ticket created successfully");
      await loadTickets();
    } catch (error) {
      approve.disabled = false;
      reject.disabled = false;
      approve.textContent = "Approve & create";
      showToast(error.message, "error");
    }
  });

  reject.addEventListener("click", async () => {
    approve.disabled = true;
    reject.disabled = true;
    reject.textContent = "Rejecting…";
    try {
      await api(`/v1/approvals/${encodeURIComponent(action.id)}/reject`, { method: "POST" });
      updateApprovalCard(card, "rejected", "No customer record was changed.");
      showToast("Proposed action rejected");
    } catch (error) {
      approve.disabled = false;
      reject.disabled = false;
      reject.textContent = "Reject";
      showToast(error.message, "error");
    }
  });
}

function appendAssistantMessage(payload) {
  const { article, content } = buildMessageShell("assistant");
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  appendMessageText(bubble, payload.message);
  content.append(bubble);

  for (const citation of payload.citations) appendCitation(content, citation);
  if (payload.proposed_action) appendApproval(content, payload.proposed_action);

  const meta = document.createElement("div");
  meta.className = "response-meta";
  const toolCount = payload.tool_calls.length;
  meta.textContent = `${toolCount} tool${toolCount === 1 ? "" : "s"} · ${payload.latency_ms.toFixed(1)} ms`;
  content.append(meta);
  elements.chatMessages.append(article);
  scrollConversation();
}

function appendErrorMessage(message) {
  const { article, content } = buildMessageShell("assistant");
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = "Could not complete request";
  const text = document.createElement("p");
  text.textContent = message;
  bubble.append(label, text);
  content.append(bubble);
  elements.chatMessages.append(article);
  scrollConversation();
}

async function sendMessage(message) {
  if (!message.trim() || state.sending) return;
  if (!state.selectedAccount) {
    showToast("Select an account before sending a message", "error");
    return;
  }

  appendUserMessage(message.trim());
  elements.input.value = "";
  resetInputHeight();
  setSending(true);
  const loading = appendLoadingMessage();
  try {
    const response = await api("/v1/support/messages", {
      method: "POST",
      body: JSON.stringify({
        account_id: state.selectedAccount.id,
        message: message.trim(),
      }),
    });
    loading.remove();
    appendAssistantMessage(response);
  } catch (error) {
    loading.remove();
    appendErrorMessage(error.message);
  } finally {
    setSending(false);
    elements.input.focus();
  }
}

function renderAccount() {
  const account = state.selectedAccount;
  if (!account) return;
  elements.accountSummary.replaceChildren();
  const avatar = document.createElement("span");
  avatar.className = "customer-avatar";
  avatar.textContent = initials(account.name);
  const copy = document.createElement("div");
  copy.className = "customer-copy";
  const name = document.createElement("strong");
  name.textContent = account.name;
  const detail = document.createElement("span");
  detail.textContent = `${account.plan} plan · ${account.id}`;
  copy.append(name, detail);
  const status = document.createElement("span");
  status.className = `account-status ${account.status === "past_due" ? "past-due" : ""}`;
  status.textContent = account.status.replaceAll("_", " ");
  elements.accountSummary.append(avatar, copy, status);
}

function renderTickets(tickets) {
  elements.ticketCount.textContent = String(tickets.length);
  elements.ticketList.replaceChildren();
  if (!tickets.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state small";
    const icon = document.createElement("span");
    icon.append(makeIcon("ticket"));
    const text = document.createElement("p");
    text.textContent = "No tickets for this account yet.";
    empty.append(icon, text);
    elements.ticketList.append(empty);
    return;
  }

  for (const ticket of tickets) {
    const item = document.createElement("article");
    item.className = "ticket-item";
    const top = document.createElement("div");
    top.className = "ticket-item-top";
    const subject = document.createElement("strong");
    subject.textContent = ticket.subject;
    subject.title = ticket.subject;
    const status = document.createElement("span");
    status.className = "ticket-status";
    status.textContent = ticket.status;
    top.append(subject, status);
    const detail = document.createElement("small");
    detail.textContent = `${ticket.id.slice(0, 8)} · ${formatDate(ticket.created_at)}`;
    item.append(top, detail);
    elements.ticketList.append(item);
  }
}

async function loadTickets() {
  if (!state.selectedAccount) return;
  try {
    const tickets = await api(`/v1/tickets?account_id=${encodeURIComponent(state.selectedAccount.id)}`);
    renderTickets(tickets);
  } catch (error) {
    showToast(`Could not load tickets: ${error.message}`, "error");
  }
}

async function loadAccounts() {
  state.accounts = await api("/v1/accounts");
  elements.accountSelect.replaceChildren();
  for (const account of state.accounts) {
    const option = document.createElement("option");
    option.value = account.id;
    option.textContent = `${account.name} — ${titleCase(account.plan)}`;
    elements.accountSelect.append(option);
  }
  state.selectedAccount = state.accounts.find((account) => account.id === "acct_1001") || state.accounts[0];
  if (state.selectedAccount) elements.accountSelect.value = state.selectedAccount.id;
  renderAccount();
  await loadTickets();
}

function setDependencyStatus(element, online) {
  element.textContent = online ? "Online" : "Unavailable";
  element.classList.toggle("online", online);
  element.classList.toggle("offline", !online);
}

function renderHealth(health) {
  state.health = health;
  const healthy = health.status === "ok";
  elements.sidebarStatus.classList.toggle("healthy", healthy);
  elements.sidebarStatus.classList.toggle("unhealthy", !healthy);
  elements.sidebarStatus.querySelector("strong").textContent = healthy ? "All systems operational" : "Service degraded";
  elements.topbarStatus.classList.toggle("healthy", healthy);
  elements.topbarStatus.classList.toggle("unhealthy", !healthy);
  elements.topbarStatus.lastChild.textContent = healthy ? " Operational" : " Degraded";
  document.querySelector("#system-health-badge").textContent = healthy
    ? "All dependencies operational"
    : "One or more dependencies unavailable";
  setDependencyStatus(document.querySelector("#postgres-status"), health.postgres);
  setDependencyStatus(document.querySelector("#redis-status"), health.redis);
}

async function loadHealth() {
  try {
    renderHealth(await api("/health"));
  } catch {
    renderHealth({ status: "degraded", postgres: false, redis: false });
  }
}

function percent(value) {
  return `${Math.round(value * 100)}%`;
}

async function loadBenchmark() {
  try {
    const benchmark = await api("/v1/benchmark");
    document.querySelector("#completion-metric").textContent = percent(benchmark.task_completion_rate);
    document.querySelector("#citation-metric").textContent = percent(benchmark.citation_correctness);
    document.querySelector("#failure-metric").textContent = String(benchmark.tool_failures);
    document.querySelector("#latency-metric").textContent = `${benchmark.latency_ms.p95.toFixed(0)} ms`;
    document.querySelector("#p50-metric").textContent = `${benchmark.latency_ms.p50.toFixed(1)} ms`;
    document.querySelector("#mean-metric").textContent = `${benchmark.latency_ms.mean.toFixed(1)} ms`;
    document.querySelector("#p95-detail-metric").textContent = `${benchmark.latency_ms.p95.toFixed(1)} ms`;
    document.querySelector("#cost-metric").textContent = `$${benchmark.average_cost_per_request_usd.toFixed(2)}`;
    const runDate = new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    }).format(new Date(benchmark.run_at));
    document.querySelector("#run-stamp").textContent = `Baseline run · ${runDate}`;
  } catch (error) {
    document.querySelector("#run-stamp").textContent = "Baseline unavailable";
    showToast(`Could not load benchmark: ${error.message}`, "error");
  }
}

function switchView(viewName) {
  const labels = {
    support: "Support inbox",
    evaluation: "Evaluation",
    system: "System",
  };
  document.querySelectorAll("[data-view-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.viewPanel === viewName);
  });
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
  });
  elements.pageTitle.textContent = labels[viewName];
  closeMobileMenu();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function openMobileMenu() {
  elements.sidebar.classList.add("open");
  elements.mobileScrim.classList.add("open");
}

function closeMobileMenu() {
  elements.sidebar.classList.remove("open");
  elements.mobileScrim.classList.remove("open");
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendMessage(elements.input.value);
});

elements.input.addEventListener("input", resetInputHeight);
elements.input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
});

elements.accountSelect.addEventListener("change", async (event) => {
  state.selectedAccount = state.accounts.find((account) => account.id === event.target.value);
  renderAccount();
  clearConversation();
  await loadTickets();
  showToast(`Switched to ${state.selectedAccount.name}`);
});

elements.clearChat.addEventListener("click", () => clearConversation(true));
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    elements.input.value = button.dataset.prompt;
    resetInputHeight();
    elements.input.focus();
  });
});
document.querySelectorAll(".nav-item").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});
document.querySelector("#menu-button").addEventListener("click", openMobileMenu);
elements.mobileScrim.addEventListener("click", closeMobileMenu);

async function initialize() {
  const results = await Promise.allSettled([loadAccounts(), loadHealth(), loadBenchmark()]);
  if (results[0].status === "rejected") {
    showToast(`Could not load accounts: ${results[0].reason.message}`, "error");
  }
  window.setInterval(loadHealth, 30000);
}

initialize();
