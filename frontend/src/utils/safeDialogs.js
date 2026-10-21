// User content must be assigned as a value, never parsed as dialog HTML.
export function copyDialogOptions(text) {
  const textarea = document.createElement('textarea');
  textarea.className = 'swal-copy-textarea';
  textarea.readOnly = true;
  textarea.value = text;
  return {
    title: '請手動複製',
    html: textarea,
    icon: 'info',
    confirmButtonText: '我知道了',
    didOpen: () => {
      textarea.focus();
      textarea.select();
    },
  };
}
