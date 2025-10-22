const backendBaseUrl = (() => {
  if (window.__BACKEND_URL__) {
    return window.__BACKEND_URL__;
  }
  const { protocol, hostname } = window.location;
  const defaultPort = 8000;
  const port = window.__BACKEND_PORT__ || defaultPort;
  return `${protocol}//${hostname}:${port}`;
})();

function normalizeUrl(url) {
  try {
    const normalized = new URL(url);
    return normalized.origin;
  } catch (error) {
    return url;
  }
}

const endpointElement = document.querySelector('#backend-endpoint');
if (endpointElement) {
  endpointElement.textContent = normalizeUrl(backendBaseUrl);
}

const yearElement = document.querySelector('#current-year');
if (yearElement) {
  yearElement.textContent = String(new Date().getFullYear());
}
