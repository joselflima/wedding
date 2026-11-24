const installation = document.querySelector('[data-install]');
const installationAction = installation.querySelector('summary');
let installPrompt;

if (navigator.standalone) {
  installation.hidden = true;
}

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  installPrompt = event;
});

installationAction.addEventListener('click', async (event) => {
  if (!installPrompt) return;

  event.preventDefault();
  const prompt = installPrompt;
  installPrompt = null;
  installation.open = false;

  try {
    await prompt.prompt();
  } catch {
    installation.open = true;
  }
});

window.addEventListener('appinstalled', () => {
  installPrompt = null;
  installation.hidden = true;
});
