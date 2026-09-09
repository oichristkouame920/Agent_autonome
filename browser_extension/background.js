"use strict";

try {
  importScripts("bridge_config.js");
} catch (_) {
  globalThis.AGENTLOCAL_BRIDGE_CONFIG = null;
}

const CONFIG = globalThis.AGENTLOCAL_BRIDGE_CONFIG;
const HARD_MAX_CLOSE_TABS = 10;
const HARD_MAX_LIST_TABS = 50;
const ALARM_NAME = "agentlocal-bridge-wakeup";

let pollTimer = null;
let pollPending = false;

function bridgeConfigured() {
  return Boolean(
    CONFIG &&
    CONFIG.enabled === true &&
    CONFIG.host === "127.0.0.1" &&
    Number.isInteger(CONFIG.port) &&
    CONFIG.port >= 1024 &&
    CONFIG.port <= 65535 &&
    typeof CONFIG.token === "string" &&
    CONFIG.token.length >= 64 &&
    typeof CONFIG.extensionId === "string" &&
    CONFIG.extensionId.length === 32
  );
}

function bridgeBaseUrl() {
  return `http://127.0.0.1:${CONFIG.port}`;
}

function bridgeHeaders(includeJson = false) {
  const headers = {
    "X-AgentLocal-Token": CONFIG.token,
    "X-AgentLocal-Extension-ID": CONFIG.extensionId
  };

  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }

  return headers;
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
      message: "URL cible refusée par l'extension AgentLocal."
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
      message: `Aucun onglet Edge correspondant à ${targetUrl} n'a été trouvé.`
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
      message: "Aucun onglet Edge fermable n'a été trouvé."
    };
  }

  await chrome.tabs.remove(ids);

  return {
    ok: true,
    closed_count: ids.length,
    message: `${ids.length} onglet(s) Edge correspondant à ${targetUrl} fermé(s).`
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
      title: typeof tab.title === "string"
        ? tab.title.slice(0, 500)
        : "",
      active: Boolean(tab.active)
    });
  }

  return {
    ok: true,
    tabs: safeTabs,
    message: `${safeTabs.length} onglet(s) web visible(s) par AgentLocal.`
  };
}

async function activateSiteCommand(command) {
  const payload = command.payload && typeof command.payload === "object"
    ? command.payload
    : {};

  const targetUrl = String(payload.url || "").trim();

  if (!parseHttpUrl(targetUrl)) {
    return {
      ok: false,
      message: "URL cible refusée par l'extension AgentLocal."
    };
  }

  const allowSubdomains = Boolean(payload.allow_subdomains);
  const tabs = await chrome.tabs.query({});

  const match = tabs.find((tab) => {
    return (
      typeof tab.id === "number" &&
      typeof tab.url === "string" &&
      hostMatches(tab.url, targetUrl, allowSubdomains)
    );
  });

  if (!match || typeof match.id !== "number") {
    return {
      ok: false,
      message: `Aucun onglet Edge correspondant à ${targetUrl} n'a été trouvé.`
    };
  }

  await chrome.tabs.update(
    match.id,
    {
      active: true
    }
  );

  if (typeof match.windowId === "number") {
    await chrome.windows.update(
      match.windowId,
      {
        focused: true
      }
    );
  }

  return {
    ok: true,
    message: `Onglet Edge activé pour ${targetUrl}.`
  };
}

async function executeCommand(command) {
  if (!command || command.type !== "command") {
    return;
  }

  const requestId = String(command.request_id || "");
  const action = String(command.action || "");

  if (!requestId || !action) {
    return;
  }

  let result;

  try {
    if (action === "close_site") {
      result = await closeSiteCommand(command);
    } else if (action === "list_tabs") {
      result = await listTabsCommand();
    } else if (action === "activate_site") {
      result = await activateSiteCommand(command);
    } else if (action === "ping") {
      result = {
        ok: true,
        message: "Pont Edge HTTP AgentLocal opérationnel."
      };
    } else {
      result = {
        ok: false,
        message: "Action de pont non autorisée."
      };
    }
  } catch (error) {
    result = {
      ok: false,
      message: `Erreur du pont Edge : ${String(
        error && error.message
          ? error.message
          : error
      )}`
    };
  }

  await postResult({
    type: "result",
    schema_version: 1,
    request_id: requestId,
    action: action,
    ...result
  });
}

async function postResult(result) {
  const response = await fetch(
    `${bridgeBaseUrl()}/v1/result`,
    {
      method: "POST",
      headers: bridgeHeaders(true),
      body: JSON.stringify(result),
      cache: "no-store"
    }
  );

  if (!response.ok) {
    throw new Error(
      `Le serveur AgentLocal a refusé le résultat (${response.status}).`
    );
  }
}

async function pollOnce() {
  if (!bridgeConfigured() || pollPending) {
    return;
  }

  pollPending = true;

  try {
    const response = await fetch(
      `${bridgeBaseUrl()}/v1/command`,
      {
        method: "GET",
        headers: bridgeHeaders(false),
        cache: "no-store"
      }
    );

    if (response.status === 204) {
      return;
    }

    if (!response.ok) {
      return;
    }

    const command = await response.json();

    if (
      command &&
      typeof command === "object" &&
      command.type === "command"
    ) {
      await executeCommand(command);
    }
  } catch (_) {
    // AgentLocal n'est peut-être pas lancé. Le prochain poll réessaiera.
  } finally {
    pollPending = false;
  }
}

function startPolling() {
  if (!bridgeConfigured()) {
    return;
  }

  if (pollTimer) {
    clearInterval(pollTimer);
  }

  const interval = clampInt(
    CONFIG.pollIntervalMs,
    250,
    2000,
    500
  );

  pollTimer = setInterval(
    () => {
      void pollOnce();
    },
    interval
  );

  chrome.alarms.create(
    ALARM_NAME,
    {
      periodInMinutes: 0.5
    }
  );

  void pollOnce();
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm && alarm.name === ALARM_NAME) {
    void pollOnce();
  }
});

chrome.runtime.onStartup.addListener(() => {
  startPolling();
});

chrome.runtime.onInstalled.addListener(() => {
  startPolling();
});

startPolling();
