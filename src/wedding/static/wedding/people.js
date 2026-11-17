const dialog = document.getElementById('participant-dialog');
document.getElementById('add-participant').addEventListener('click', () => dialog.showModal());
for (const id of ['close-participant', 'cancel-participant']) {
  document.getElementById(id).addEventListener('click', () => dialog.close());
}
if (dialog.dataset.invalid === 'true') dialog.showModal();
