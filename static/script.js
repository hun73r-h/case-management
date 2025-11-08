// Alert when form is submitted
document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", function () {
            alert("New case added successfully!");
        });
    }

    // Confirm before marking received
    const receivedLinks = document.querySelectorAll("a[href*='/received/']");
    receivedLinks.forEach(function (link) {
        link.addEventListener("click", function (event) {
            const confirmed = confirm("Are you sure you want to mark this case as received?");
            if (!confirmed) {
                event.preventDefault();
            }
        });
    });
});
