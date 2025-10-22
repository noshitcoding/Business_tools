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
const healthButton = document.querySelector('#health-check');
const healthResult = document.querySelector('#health-result');
const openItemsForm = document.querySelector('#open-items-form');
const openItemsResult = document.querySelector('#open-items-result');
const consoleForm = document.querySelector('#console-form');
const consoleResult = document.querySelector('#console-result');

function displayResult(container, payload, isError = false) {
  container.classList.toggle('error', isError);
  container.textContent = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
}

async function fetchFromBackend(path) {
  const url = new URL(path, backendBaseUrl);
  const response = await fetch(url);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${message}`);
  }
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
}

healthButton.addEventListener('click', async () => {
  displayResult(healthResult, 'Lade...');
  try {
    const data = await fetchFromBackend('/health');
    displayResult(healthResult, data);
  } catch (error) {
    displayResult(healthResult, error.message, true);
  }
});

openItemsForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const organizationId = Number.parseInt(event.target['organization-id'].value, 10);
  if (!Number.isFinite(organizationId)) {
    displayResult(openItemsResult, 'Ungültige Organisation-ID.', true);
    return;
  }
  displayResult(openItemsResult, 'Lade...');
  try {
    const data = await fetchFromBackend(`/invoices/open?organization_id=${organizationId}`);
    displayResult(openItemsResult, data);
  } catch (error) {
    displayResult(openItemsResult, error.message, true);
  }
});

consoleForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const pathInput = event.target['console-path'].value || '/';
  displayResult(consoleResult, 'Lade...');
  try {
    const data = await fetchFromBackend(pathInput);
    displayResult(consoleResult, data);
  } catch (error) {
    displayResult(consoleResult, error.message, true);
  }
});

// Trigger initial health check to inform the user right away.
healthButton.click();
