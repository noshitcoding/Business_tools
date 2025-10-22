// Dieses Template wird beim Start des Frontend-Containers in env.js überführt.
// Die Werte werden durch Umgebungsvariablen ersetzt, um das Backend dynamisch zu adressieren.
(function configureRuntimeEnv() {
  const configuredUrl = '${BACKEND_URL}'.trim();
  const configuredPort = '${BACKEND_PORT}'.trim();
  if (configuredUrl && configuredUrl !== '${' + 'BACKEND_URL' + '}') {
    window.__BACKEND_URL__ = configuredUrl;
  }
  if (configuredPort && configuredPort !== '${' + 'BACKEND_PORT' + '}') {
    const numericPort = Number.parseInt(configuredPort, 10);
    if (Number.isFinite(numericPort)) {
      window.__BACKEND_PORT__ = numericPort;
    }
  }
})();
