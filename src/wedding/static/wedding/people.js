function enableBackdropClose(dialogElement) {
  dialogElement.addEventListener('click', (event) => {
    if (event.target !== dialogElement) return;
    const rect = dialogElement.getBoundingClientRect();
    const clickedOutside =
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom;
    if (clickedOutside) dialogElement.close();
  });
}

const dialog = document.getElementById('participant-dialog');
if (dialog) {
  document.getElementById('add-participant')?.addEventListener('click', () => dialog.showModal());
  for (const id of ['close-participant', 'cancel-participant']) {
    document.getElementById(id)?.addEventListener('click', () => dialog.close());
  }
  enableBackdropClose(dialog);
  if (dialog.dataset.invalid === 'true') dialog.showModal();
}

const editDialog = document.getElementById('edit-participant-dialog');
if (editDialog) {
  const editLink = document.querySelector(`.responsive-table a[href="${window.location.pathname}"]`);
  for (const button of editDialog.querySelectorAll('[data-close-edit]')) {
    button.addEventListener('click', () => editDialog.close());
  }
  enableBackdropClose(editDialog);
  editDialog.addEventListener('close', () => {
    window.history.replaceState(null, '', '/people/' + window.location.search);
    editLink?.focus();
  });
  editDialog.showModal();
  if (editDialog.querySelector('#activation-link')) {
    editDialog.scrollTop = 0;
  }
}
