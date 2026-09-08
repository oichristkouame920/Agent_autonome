"use strict";

const HOST_NAME = "com.agentlocal.bridge";
const POLL_INTERVAL_MS = 350;
const RECONNECT_DELAY_MS = 1500;
const HARD_MAX_CLOSE_TABS = 10;
const HARD_MAX_LIST_TABS = 50;

let nativePort = null;
let pollTimer = null;
let pollPending = false;
let reconnectTimer = null;

function safePost(message) {
  if (!nativePort) {
    return false;
  }

  try {
    nativePort.postMessage(message);
    return true;
  } catch (_) {
    return false;
  }
}

function normalizeHostname(hostname) {
  let value = String(hostname || "").trim().toLowerCase();

  if (value.startsWith("www.")) {
    value = value.slice(4);
  }

  return value.replace(/\.$/, "");
}

function parseHttpUrl(value) {
  try {
    const parsed = new URL(String(value || ""));

    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
      return null;
    }

    if (!parsed.hostname) {
      return null;
    }

    return parsed;
  } catch (_) {
    return null;
  }
}

function hostMatches(tabUrl, targetUrl, allowSubdomains) {
  const tab = parseHttpUrl(tabUrl);
  const target = parseHttpUrl(targetUrl);

  if (!tab || !target) {
    return false;
  }

  const tabHost = normalizeHostname(tab.hostname);
  const targetHost = normalizeHostname(target.hostname);

  if (!tabHost || !targetHost) {
    return false;
  }

  if (tabHost === targetHost) {
    return true;
  }

  if (
    allowSubdomains &&
    tabHost.endsWith("." + targetHost)
  ) {
    return true;
  }

  return false;
}

function clampInt(value, minimum, maximum, fallback) {
  const numeric = Number.parseInt(value, 10);

  if (!Number.isFinite(numeric)) {
    return fallback;
  }

  return Math.max(minimum, Math.min(maximum, numeric));
}

async function closeSiteCommand(command) {
  const payload = command.payload && typeof command.payload === "object"
    ? command.payload
    : {};

  const targetUrl = String(payload.url || "").trim();
  const parsedTarget = parseHttpUrl(targetUrl);

  if (!parsedTarget) {
    return {
      ok: false,
      closed_count: 0,
      message: "URL cible refusee par l'extension AgentLocal."
    };
  }

  const allowSubdomains = Boolean(payload.allow_subdomains);
  const closeAll = Boolean(payload.close_all);
  const maximumTabs = clampInt(
    payload.maximum_tabs,
    1,
    HARD_MAX_CLOSE_TABS,
    1
  );

  const tabs = await chrome.tabs.query({});

  const matches = tabs.filter((tab) => {
    return (
      typeof tab.id === "number" &&
      typeof tab.url === "string" &&
      hostMatches(tab.url, targetUrl, allowSubdomains)
    );
  });

  if (matches.length === 0) {
    return {
      ok: false,
      closed_count: 0,
      message: `Aucun onglet Edge correspondant a ${targetUrl} n'a ete trouve.`
    };
  }

  matches.sort((a, b) => {
    if (Boolean(a.active) !== Boolean(b.active)) {
      return a.active ? -1 : 1;
    }

    return (a.index || 0) - (b.index || 0);
  });

  const selected = closeAll
    ? matches.slice(0, maximumTabs)
    : matches.slice(0, 1);

  const ids = selected
    .map((tab) => tab.id)
    .filter((id) => typeof id === "number");

  if (ids.length === 0) {
    return {
      ok: false,
      closed_count: 0,
      message: "Aucun onglet Edge fermable n'a ete trouve."
    };
  }

  await chrome.tabs.remove(ids);

  return {
    ok: true,
    closed_count: ids.length,
    message: `${ids.length} onglet(s) Edge correspondant a ${targetUrl} ferme(s).`
  };
}

async function listTabsCommand() {
  const tabs = await chrome.tabs.query({});

  const safeTabs = [];

  for (const tab of tabs.slice(0, HARD_MAX_LIST_TABS)) {
    if (typeof tab.url !== "string") {
      continue;
    }

    const parsed = parseHttpUrl(tab.url);

    if (!parsed) {
      continue;
    }

    safeTabs.push({
      url: tab.url.slice(0, 4096),
      title: typeof tab.title === "string" ? tab.title.slice(0, 500) : "",
      active: Boolean(tab.active)
    });
  }

  return {
    ok: true,
    tabs: safeTabs,
    message: `${safeTabs.length} onglet(s) web visible(s) par AgentLocal.`
  };
}

async function executeCommand(command) {
  if (!command || command.type !== "command") {
    return;
  }

  const requestId = String(command.request_id || "");
  const token = String(command.token || "");
  const action = String(command.action || "");

  if (!requestId || !token || !action) {
    return;
  }

  let result;

  try {
    if (action === "close_site") {
      result = await closeSiteCommand(command);
    } else if (action === "list_tabs") {
      result = await listTabsCommand();
    } else if (action === "ping") {
      result = {
        ok: true,
        message: "Pont Edge AgentLocal operationnel."
      };
    } else {
      result = {
        ok: false,
        message: "Action de pont non autorisee."
      };
    }
  } catch (error) {
    result = {
      ok: false,
      message: `Erreur du pont Edge : ${String(error && error.message ? error.message : error)}`
    };
  }

  safePost({
    type: "result",
    schema_version: 1,
    request_id: requestId,
    token: token,
    action: action,
    ...result
  });
}

function scheduleReconnect() {
  if (reconnectTimer) {
    return;
  }

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectNativeHost();
  }, RECONNECT_DELAY_MS);
}

function startPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
  }

  pollTimer = setInterval(() => {
    if (!nativePort || pollPending) {
      return;
    }

    pollPending = safePost({
      type: "poll",
      schema_version: 1
    });
  }, POLL_INTERVAL_MS);
}

function connectNativeHost() {
  try {
    nativePort = chrome.runtime.connectNative(HOST_NAME);
  } catch (_) {
    nativePort = null;
    scheduleReconnect();
    return;
  }

  nativePort.onMessage.addListener((message) => {
    pollPending = false;

    if (!message || typeof message !== "object") {
      return;
    }

    if (message.type === "command") {
      void executeCommand(message);
    }
  });

  nativePort.onDisconnect.addListener(() => {
    nativePort = null;
    pollPending = false;

    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }

    scheduleReconnect();
  });

  safePost({
    type: "hello",
    schema_version: 1
  });

  startPolling();
}

connectNativeHost();
