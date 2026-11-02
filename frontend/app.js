"use strict";

const form = document.querySelector("#shorten-form");
const input = document.querySelector("#original-url");
const submitButton = document.querySelector("#shorten-button");
const formMessage = document.querySelector("#form-message");
const result = document.querySelector("#result");
const shortLink = document.querySelector("#short-url");
const copyButton = document.querySelector("#copy-button");
const copyMessage = document.querySelector("#copy-message");
const refreshButton = document.querySelector("#refresh-button");
const clickCount = document.querySelector("#click-count");
const statsMessage = document.querySelector("#stats-message");
let currentCode = null;

function message(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle("error", isError);
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal });
    if (!response.ok) {
      if (response.status === 422) throw new Error("Please enter a valid HTTP or HTTPS URL.");
      if (response.status === 404) throw new Error("This short link could not be found.");
      throw new Error("The service is unavailable. Please try again shortly.");
    }
    return await response.json();
  } catch (error) {
    if (error.name === "AbortError") throw new Error("The request timed out. Please try again.");
    if (error instanceof TypeError) throw new Error("Could not connect. Check your connection and try again.");
    if (error instanceof SyntaxError) throw new Error("The service returned an invalid response. Please try again.");
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function refreshStats() {
  const code = currentCode;
  if (!code || refreshButton.disabled) return;
  refreshButton.disabled = true;
  refreshButton.textContent = "Refreshing…";
  message(statsMessage, "Loading statistics…");
  try {
    const data = await request(`/api/urls/${encodeURIComponent(code)}/stats`);
    if (data.code !== code || !Number.isSafeInteger(data.click_count) || data.click_count < 0) {
      throw new Error("Statistics are temporarily unavailable. Please try again.");
    }
    if (currentCode !== code) return;
    clickCount.textContent = String(data.click_count);
    message(statsMessage, "Statistics updated.");
  } catch (error) {
    if (currentCode !== code) return;
    clickCount.textContent = "—";
    message(statsMessage, error.message, true);
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Refresh stats";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (submitButton.disabled) return;
  input.removeAttribute("aria-invalid");
  let originalUrl;
  try {
    originalUrl = new URL(input.value.trim());
    if (!["http:", "https:"].includes(originalUrl.protocol)) throw new Error();
  } catch {
    input.setAttribute("aria-invalid", "true");
    message(formMessage, "Enter a full URL starting with https:// or http://.", true);
    input.focus();
    return;
  }
  submitButton.disabled = true;
  submitButton.textContent = "Shortening…";
  form.setAttribute("aria-busy", "true");
  message(formMessage, "Creating your short link…");
  try {
    const data = await request("/api/urls", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: originalUrl.href }),
    });
    if (typeof data.code !== "string" || !/^[a-zA-Z0-9]{7}$/.test(data.code)) {
      throw new Error("The service returned an invalid short link. Please try again.");
    }
    currentCode = data.code;
    // Build from this origin so links also work behind the reverse proxy.
    const path = `/r/${encodeURIComponent(currentCode)}`;
    shortLink.setAttribute("href", path);
    shortLink.textContent = new URL(path, window.location.origin).href;
    result.hidden = false;
    clickCount.textContent = "—";
    message(copyMessage, "");
    message(formMessage, "Your short link is ready.");
    // A previous stats request may still be finishing; wait for it before refreshing.
    if (!refreshButton.disabled) void refreshStats();
    else message(statsMessage, "Select Refresh stats to load the new link’s count.");
  } catch (error) {
    message(formMessage, error.message, true);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Shorten URL";
    form.removeAttribute("aria-busy");
  }
});

copyButton.addEventListener("click", async () => {
  if (!currentCode) return;
  const url = shortLink.textContent;
  copyButton.disabled = true;
  try {
    await navigator.clipboard.writeText(url);
    if (shortLink.textContent === url) message(copyMessage, "Copied to clipboard.");
  } catch {
    message(copyMessage, "Copy isn’t available here. Select and copy the short link above.", true);
  } finally {
    copyButton.disabled = false;
  }
});
refreshButton.addEventListener("click", refreshStats);
