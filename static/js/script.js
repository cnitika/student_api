document.addEventListener("DOMContentLoaded", function () {
    // Delete Confirmation Handler
    const deleteForms = document.querySelectorAll(".delete-form");
    deleteForms.forEach(function (form) {
        form.addEventListener("submit", function (e) {
            const item = form.getAttribute("data-item-name") || "this item";
            const confirmed = confirm("Are you sure you want to delete " + item + "? This action cannot be undone.");
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });

    // Print Button Handler
    const printButtons = document.querySelectorAll(".btn-print");
    printButtons.forEach(function (btn) {
        btn.addEventListener("click", function () {
            window.print();
        });
    });

    // Subject Max Marks dynamic display on selection
    const subjectSelect = document.getElementById("subject_id_select");
    const maxMarksHint = document.getElementById("max_marks_hint");
    if (subjectSelect && maxMarksHint) {
        subjectSelect.addEventListener("change", function () {
            const selectedOpt = subjectSelect.options[subjectSelect.selectedIndex];
            const maxVal = selectedOpt.getAttribute("data-max-marks");
            if (maxVal) {
                maxMarksHint.textContent = "(Max Marks: " + maxVal + ")";
            } else {
                maxMarksHint.textContent = "";
            }
        });
    }

    // Add row to dynamic marks entry form if present
    const addRowBtn = document.getElementById("add_mark_row_btn");
    const marksContainer = document.getElementById("marks_rows_container");
    if (addRowBtn && marksContainer) {
        addRowBtn.addEventListener("click", function () {
            const firstRow = marksContainer.querySelector(".mark-row");
            if (firstRow) {
                const newRow = firstRow.cloneNode(true);
                // Clear input values in new row
                const inputs = newRow.querySelectorAll("input");
                inputs.forEach(function (inp) { inp.value = ""; });
                const selects = newRow.querySelectorAll("select");
                selects.forEach(function (sel) { sel.selectedIndex = 0; });
                marksContainer.appendChild(newRow);
            }
        });
    }
});
