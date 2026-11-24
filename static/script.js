// Ask for confirmation before sending money.
const transferForm = document.getElementById("transfer-form");

if (transferForm) {
    transferForm.addEventListener("submit", (event) => {
        const to = document.getElementById("to").value;
        const amount = parseFloat(document.getElementById("amount").value).toFixed(2);

        if (!confirm(`Send $${amount} to ${to}?`)) {
            event.preventDefault(); // cancel the submit
        }
    });
}

// Fade out flash messages after 4 seconds.
document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
        el.style.transition = "opacity 0.5s";
        el.style.opacity = "0";
        setTimeout(() => el.remove(), 500);
    }, 4000);
});
