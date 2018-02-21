var insertConditionInContent = function() {
  var btn = $(this);
  var range = $("#id_content").summernote('createRange');
  condition_text = 'YOUR TEXT HERE';
  range_text = range.toString();
  if (range_text != '') {
    condition_text = range_text;
  }
  insert_text = "{% if " + btn.attr('data-name') +
      " %}" + condition_text + "{% endif %}";
  $('#id_content').summernote('editor.insertText', insert_text);
};

var insertAttributeInContent = function() {
  var val = $(this).val();
  if (val == '') {
    return;
  }
  insert_text = "{{ " + val + " }}";
  $('#id_content').summernote('editor.insertText', insert_text);
  $(this).val(this.defaultSelected);
}

$(function () {
  $('#checkAll').click(function () {    
       $('input:checkbox').prop('checked', this.checked);    
   });

  // Create Action
  $(".js-create-action").click(loadForm);
  $("#modal-item").on("submit", ".js-action-create-form", saveForm);

  // Update Action
  $("#action-table").on("click", ".js-action-update", loadForm);
  $("#modal-item").on("submit", ".js-action-update-form", saveForm);

  // Delete Action
  $("#action-table").on("click", ".js-action-delete", loadForm);
  $("#modal-item").on("submit", ".js-action-delete-form", saveForm);

  // Clone Action
  $("#action-table").on("click", ".js-action-clone", loadForm);
  $("#modal-item").on("submit", ".js-action-clone-form", saveForm);

  // Create filter
  $("#filter-set").on("click", ".js-filter-create", loadForm);
  $("#modal-item").on("submit", ".js-filter-create-form", saveForm);

  // Edit Filter
  $("#filter-set").on("click", ".js-filter-edit", loadForm);
  $("#modal-item").on("submit", ".js-filter-edit-form", saveForm);

  // Delete Filter
  $("#filter-set").on("click", ".js-filter-delete", loadForm);
  $("#modal-item").on("submit", ".js-filter-delete-form", saveForm);

  // Create Condition
  $("#condition-set").on("click", ".js-condition-create", loadForm);
  $("#modal-item").on("submit", ".js-condition-create-form", saveForm);

  // Edit Condition
  $("#condition-set").on("click", ".js-condition-edit", loadForm);
  $("#modal-item").on("submit", ".js-condition-edit-form", saveForm);

  // Delete Condition
  $("#condition-set").on("click", ".js-condition-delete", loadForm);
  $("#modal-item").on("submit", ".js-condition-delete-form", saveForm);

  // Insert condition blurb in the editor
  $("#condition-set").on("click", ".js-condition-insert",
    insertConditionInContent);

  // Insert attribute in content
  $("#attribute-names").on("change",
                           "#select-attribute-name",
                           insertAttributeInContent);
  // Insert attribute column in content
  $("#attribute-names").on("change",
                           "#select-column-name",
                           insertAttributeInContent);

  // Preview
  $("#html-editor").on("click", ".js-action-preview", loadForm);
  $("#email-action-request-data").on("click", ".js-email-preview", loadForm);
  $(".modal-content").on("click", ".js-action-preview-nxt", loadForm);
  $(".modal-content").on("click", ".js-action-preview-prv", loadForm);

  // Show URL
  $("#action-table").on("click", ".js-action-showurl", loadForm);
  $("#modal-item").on("submit", ".js-action-showurl-form", saveForm);
});


