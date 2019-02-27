$(function () {
  $("#checkAll").click(function () {
       $("input[id*='id_select_']").prop("checked", this.checked);
  });

  // Create Workflow
  $(".js-create-workflow").click(loadForm);
  $("#modal-item").on("submit", ".js-workflow-create-form", saveForm);

  // Delete Workflow
  $("#workflow-index, #workflow-detail").on(
    "click",
    ".js-workflow-delete",
    loadForm);
  $("#modal-item").on("submit", ".js-workflow-delete-form", saveForm);

  // Update Workflow
  $("#workflow-index, #workflow-detail").on(
    "click",
    ".js-workflow-update",
    loadForm);
  $("#modal-item").on("submit", ".js-workflow-update-form", saveForm);

  // Clone workflow
  $("#workflow-index, #workflow-detail").on(
    "click",
    ".js-workflow-clone",
    loadForm);
  $("#modal-item").on("submit", ".js-workflow-clone-form", saveForm);

  // Flush workflow in detail view
  $("#workflow-index, #workflow-detail").on(
    "click",
    ".js-workflow-flush",
    loadForm);
  $("#modal-item").on("submit", ".js-workflow-flush-form", saveForm);

  // Add/Edit attribute
  $("#workflow-attributes").on("click", ".js-attribute-create", loadForm);
  $("#workflow-attributes").on("click", ".js-attribute-edit", loadForm);
  $("#modal-item").on("submit", ".js-attribute-create-form", saveForm);

  // Delete attribute
  $("#attribute-table").on("click", ".js-attribute-delete", loadForm);
  $("#modal-item").on("submit", ".js-attribute-delete-form", saveForm);

  // Add Share
  $("#workflow-shared").on("click", ".js-share-create", loadForm);
  $("#modal-item").on("submit", ".js-share-create-form", saveForm);

  // Delete share
  $("#share-table").on("click", ".js-share-delete", loadForm);
  $("#modal-item").on("submit", ".js-share-delete-form", saveForm);

  // Column Add
  $("#workflow-detail").on("click", ".js-workflow-column-add", loadForm);
  $("#modal-item").on("submit", ".js-workflow-column-add-form", saveForm);

  // Derived column add
  $("#workflow-index").on("click", ".js-workflow-formula-column-add", loadForm);
  $("#modal-item").on("submit", ".js-workflow-formula-column-add-form",
  saveForm);

  // Random column add
  $("#workflow-index").on("click", ".js-workflow-random-column-add", loadForm);
  $("#modal-item").on("submit", ".js-workflow-random-column-add-form",
  saveForm);

  // Column Edit
  $("#column-table").on("click", ".js-workflow-column-edit", loadForm);
  $("#modal-item").on("submit", ".js-column-edit-form", saveForm);

  // Delete column
  $("#column-table").on("click", ".js-column-delete", loadForm);
  $("#modal-item").on("submit", ".js-column-delete-form", saveForm);

  // Clone column
  $("#column-table").on("click", ".js-column-clone", loadForm);
  $("#modal-item").on("submit", ".js-column-clone-form", saveForm);

  // Restrict column
  $("#column-table").on("click", ".js-column-restrict", loadForm);
  $("#modal-item").on("submit", ".js-column-restrict-form", saveForm);

  $(".card").hover(function(){
    $(this).css("background-color", "lightgray");
  }, function(){
    $(this).css("background-color", "white");
  });
});
window.onload = function(){
  setDateTimePickers();
};
$(".ontask-card .card-body, .ontask-card .card-header").click(function() {
  window.location = $(this).parent().find("a").attr("href");
  $('#div-spinner').show();
  return false;
});
$(document).ready(function() {
  if (location.hash) {
    $("a[href='" + location.hash + "']").tab("show");
  }
  $(document.body).on("click", "a[data-toggle]", function(event) {
    location.hash = this.getAttribute("href");
  });
});
$(window).on("popstate", function() {
  var anchor = location.hash || $("a[data-toggle='tab']").first().attr("href");
  $("a[href='" + anchor + "']").tab("show");
});
