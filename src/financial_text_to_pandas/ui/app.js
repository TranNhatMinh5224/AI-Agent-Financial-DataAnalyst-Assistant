const API_URL = "http://localhost:8000";
let currentRunId = null;

const elements = {
    questionInput: document.getElementById("questionInput"),
    askBtn: document.getElementById("askBtn"),
    askText: document.querySelector(".btn-text"),
    askLoader: document.getElementById("askLoader"),
    resultContainer: document.getElementById("resultContainer"),
    answerValue: document.getElementById("answerValue"),
    verificationBadge: document.getElementById("verificationBadge"),
    unitBadge: document.getElementById("unitBadge"),
    traceCode: document.getElementById("traceCode"),
    btnThumbUp: document.getElementById("btnThumbUp"),
    btnThumbDown: document.getElementById("btnThumbDown"),
    feedbackThanks: document.getElementById("feedbackThanks")
};

elements.askBtn.addEventListener("click", handleAsk);
elements.questionInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleAsk();
});

elements.btnThumbUp.addEventListener("click", () => sendFeedback("up"));
elements.btnThumbDown.addEventListener("click", () => sendFeedback("down"));

async function handleAsk() {
    const question = elements.questionInput.value.trim();
    if (!question) return;

    // Loading state
    elements.askText.classList.add("hidden");
    elements.askLoader.classList.remove("hidden");
    elements.askBtn.disabled = true;
    elements.resultContainer.classList.add("hidden");
    elements.feedbackThanks.classList.add("hidden");

    try {
        const res = await fetch(`${API_URL}/qa/answer`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question })
        });
        
        const data = await res.json();
        
        currentRunId = data.run_id;
        
        // Populate UI
        elements.answerValue.textContent = data.answer.toLocaleString();
        
        elements.unitBadge.textContent = data.unit ? `Unit: ${data.unit}` : "Unit: N/A";
        
        elements.verificationBadge.textContent = data.verification_status.toUpperCase();
        elements.verificationBadge.className = "badge";
        if (data.verification_status === "valid") {
            elements.verificationBadge.classList.add("badge-success");
        } else {
            elements.verificationBadge.classList.add("badge-error");
        }

        let traceText = "";
        if (data.code_generated) {
            traceText += "=== LLM Code Generated ===\n" + data.code_generated + "\n\n";
        }
        traceText += "=== Execution Trace ===\n" + (data.trace || "No trace available.");
        if (data.error_type) {
            traceText += "\n\nError Type: " + data.error_type;
        }
        elements.traceCode.textContent = traceText;

        // Show result
        elements.resultContainer.classList.remove("hidden");

    } catch (error) {
        console.error("Error:", error);
        alert("Failed to connect to the server.");
    } finally {
        elements.askText.classList.remove("hidden");
        elements.askLoader.classList.add("hidden");
        elements.askBtn.disabled = false;
    }
}

async function sendFeedback(rating) {
    if (!currentRunId) return;
    
    try {
        await fetch(`${API_URL}/feedback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                run_id: currentRunId,
                question: elements.questionInput.value,
                answer: parseFloat(elements.answerValue.textContent.replace(/,/g, '')),
                retrieved_table_ids: [],
                grounded_cells_json: "[]",
                selected_cells_json: "[]",
                reasoning_strategy: "auto",
                verifier_status: elements.verificationBadge.textContent.toLowerCase(),
                user_rating: rating,
                user_comment: "",
                error_type: null
            })
        });
        
        elements.feedbackThanks.classList.remove("hidden");
    } catch (error) {
        console.error("Feedback error:", error);
    }
}
