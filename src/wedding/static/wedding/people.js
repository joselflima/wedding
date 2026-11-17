const dialog = document.getElementById('participant-dialog');
document.getElementById('add-participant').addEventListener('click', () => dialog.showModal());
for (const id of ['close-participant', 'cancel-participant']) {
  document.getElementById(id).addEventListener('click', () => dialog.close());
}
if (dialog.dataset.invalid === 'true') dialog.showModal();

const editDialog = document.getElementById('edit-participant-dialog');
if (editDialog) {
  const editLink = document.querySelector(`a[href="${window.location.pathname}"]`);
  for (const button of editDialog.querySelectorAll('[data-close-edit]')) {
    button.addEventListener('click', () => editDialog.close());
  }
  editDialog.addEventListener('close', () => {
    window.history.replaceState(null, '', '/people/' + window.location.search);
    editLink?.focus();
  });
  editDialog.showModal();
}
