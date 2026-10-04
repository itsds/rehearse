(function () {
    "use strict";

    const panel = document.getElementById("coding-panel");
    if (!panel) {
        return;
    }

    const interviewId = panel.dataset.interviewId || "";
    const llmRequestTimeoutSeconds = Number(panel.dataset.llmTimeout || 60);

    let completeWs = null;
    let completeReconnectTimer = null;
    let isEndingInterview = false;
    let evaluationWatchdogTimer = null;

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const completeWsUrl =
        wsProtocol +
        "//" +
        window.location.host +
        "/interview/" +
        encodeURIComponent(interviewId) +
        "/theory/ws";

    function showCompleteEvaluating(visible) {
        const indicator = document.getElementById("coding-evaluating-indicator");
        if (indicator) {
            indicator.hidden = !visible;
        }
    }

    function clearEvaluationWatchdog() {
        if (evaluationWatchdogTimer) {
            clearTimeout(evaluationWatchdogTimer);
            evaluationWatchdogTimer = null;
        }
    }

    function startEvaluationWatchdog() {
        clearEvaluationWatchdog();
        const graceMs = 15000;
        const timeoutMs = llmRequestTimeoutSeconds * 1000 + graceMs;
        evaluationWatchdogTimer = setTimeout(function () {
            evaluationWatchdogTimer = null;
            if (!isEndingInterview) {
                return;
            }
            showCompleteEvaluating(false);
            isEndingInterview = false;
            const endBtn = document.getElementById("coding-end-btn");
            if (endBtn) {
                endBtn.disabled = false;
            }
            alert(
                "Final evaluation is taking too long. Check /config and try again."
            );
        }, timeoutMs);
    }

    function connectCompleteWebSocket() {
        completeWs = new WebSocket(completeWsUrl);

        completeWs.onopen = function () {
            if (completeReconnectTimer) {
                clearTimeout(completeReconnectTimer);
                completeReconnectTimer = null;
            }
        };

        completeWs.onmessage = function (event) {
            const data = JSON.parse(event.data);
            if (data.type === "evaluating") {
                showCompleteEvaluating(true);
                startEvaluationWatchdog();
            } else if (data.type === "interview_completed") {
                clearEvaluationWatchdog();
                showCompleteEvaluating(false);
                window.location.href =
                    "/interview/" +
                    encodeURIComponent(interviewId) +
                    "/results";
            } else if (data.type === "error") {
                clearEvaluationWatchdog();
                showCompleteEvaluating(false);
                isEndingInterview = false;
                const endBtn = document.getElementById("coding-end-btn");
                if (endBtn) {
                    endBtn.disabled = false;
                }
                alert(data.message || "Failed to complete interview.");
            }
        };

        completeWs.onclose = function () {
            if (isEndingInterview) {
                clearEvaluationWatchdog();
                showCompleteEvaluating(false);
                isEndingInterview = false;
                const endBtn = document.getElementById("coding-end-btn");
                if (endBtn) {
                    endBtn.disabled = false;
                }
            }
            completeReconnectTimer = setTimeout(
                connectCompleteWebSocket,
                3000
            );
        };
    }

    function endCodingInterview() {
        if (!confirm("Are you sure you want to end this interview?")) {
            return;
        }
        if (isEndingInterview) {
            return;
        }
        isEndingInterview = true;
        const endBtn = document.getElementById("coding-end-btn");
        if (endBtn) {
            endBtn.disabled = true;
        }
        showCompleteEvaluating(true);
        startEvaluationWatchdog();
        if (!completeWs || completeWs.readyState !== WebSocket.OPEN) {
            connectCompleteWebSocket();
            setTimeout(function () {
                if (completeWs && completeWs.readyState === WebSocket.OPEN) {
                    completeWs.send(
                        JSON.stringify({ type: "complete" })
                    );
                }
            }, 500);
            return;
        }
        completeWs.send(JSON.stringify({ type: "complete" }));
    }

    document.addEventListener("DOMContentLoaded", function () {
        connectCompleteWebSocket();
        const endBtn = document.getElementById("coding-end-btn");
        if (endBtn) {
            endBtn.addEventListener("click", endCodingInterview);
        }
    });
})();