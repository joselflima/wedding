async function copyInputValue(input) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(input.value);
      return true;
    } catch {
      // Fallback to manual selection copy when clipboard permission is unavailable.
    }
  }
  input.focus();
  input.select();
  input.setSelectionRange(0, input.value.length);
  return document.execCommand('copy');
}

for (const button of document.querySelectorAll('[data-copy-target]')) {
  const target = document.querySelector(button.dataset.copyTarget);
  if (!target) continue;

  const feedback = button.closest('.copy-callout')?.querySelector('[data-copy-feedback]');
  const defaultLabel = button.textContent.trim();
  let resetTimer;

  button.addEventListener('click', async () => {
    const copied = await copyInputValue(target);
    if (!copied) return;

    button.textContent = 'Link copiado';
    button.classList.add('is-copied');
    if (feedback) feedback.textContent = 'Link copiado para a área de transferência.';

    window.clearTimeout(resetTimer);
    resetTimer = window.setTimeout(() => {
      button.textContent = defaultLabel;
      button.classList.remove('is-copied');
      if (feedback) feedback.textContent = '';
    }, 2500);
  });
}

for (const input of document.querySelectorAll('input[readonly][data-select-on-click]')) {
  input.addEventListener('click', () => input.select());
}
