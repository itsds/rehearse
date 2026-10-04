/* Camera self-view for interview pages (templates/_self_view.html).
   Uses getUserMedia for video only, so it never competes with dictation or
   spoken answers for the microphone. The stream stays in the browser.
   Off by default; the on/off and mirror choices are remembered per browser. */
(function () {
    "use strict";

    var STORAGE_KEY = "rehearse-self-view";

    function loadPrefs() {
        var prefs = { enabled: false, mirrored: true };
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                var saved = JSON.parse(raw);
                prefs.enabled = saved.enabled === true;
                prefs.mirrored = saved.mirrored !== false;
            }
        } catch (e) { /* storage blocked: keep defaults */ }
        return prefs;
    }

    function savePrefs(prefs) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); } catch (e) { /* ignore */ }
    }

    function errorMessage(error) {
        var name = error && error.name;
        if (name === "NotAllowedError" || name === "SecurityError") {
            return "Camera permission is blocked. Allow it in the browser's site settings to use self-view.";
        }
        if (name === "NotFoundError" || name === "OverconstrainedError") {
            return "No camera found.";
        }
        if (name === "NotReadableError" || name === "AbortError") {
            return "The camera is in use by another app.";
        }
        return "Could not start the camera.";
    }

    function init(root) {
        var toggle = root.querySelector("[data-self-view-toggle]");
        var frame = root.querySelector("[data-self-view-frame]");
        var video = root.querySelector("[data-self-view-video]");
        var mirrorRow = root.querySelector("[data-self-view-mirror-row]");
        var mirror = root.querySelector("[data-self-view-mirror]");
        var status = root.querySelector("[data-self-view-status]");
        if (!toggle || !frame || !video || !mirror || !status) return;

        var prefs = loadPrefs();
        var stream = null;
        var starting = false;

        function showStatus(text) {
            status.textContent = text || "";
            status.hidden = !text;
        }

        function applyMirror() {
            mirror.checked = prefs.mirrored;
            video.classList.toggle("self-view__video--mirrored", prefs.mirrored);
        }

        function render(on) {
            toggle.textContent = on ? "Camera off" : "Camera on";
            toggle.setAttribute("aria-pressed", on ? "true" : "false");
            frame.hidden = !on;
            mirrorRow.hidden = !on;
        }

        function release() {
            if (stream) {
                stream.getTracks().forEach(function (track) { track.stop(); });
                stream = null;
            }
            video.srcObject = null;
        }

        function stop(remember) {
            release();
            render(false);
            if (remember) {
                prefs.enabled = false;
                savePrefs(prefs);
            }
        }

        async function start() {
            if (stream || starting) return;
            starting = true;
            toggle.disabled = true;
            showStatus("");
            try {
                var media = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 640 }, height: { ideal: 360 }, facingMode: "user" },
                    audio: false
                });
                stream = media;
                video.srcObject = media;
                media.getVideoTracks().forEach(function (track) {
                    // Camera unplugged or taken by the OS mid-interview.
                    track.addEventListener("ended", function () {
                        stop(false);
                        showStatus("The camera stopped.");
                    });
                });
                render(true);
                prefs.enabled = true;
                savePrefs(prefs);
            } catch (error) {
                release();
                render(false);
                // Don't auto-retry a failing camera on every page load.
                prefs.enabled = false;
                savePrefs(prefs);
                showStatus(errorMessage(error));
            } finally {
                starting = false;
                toggle.disabled = false;
            }
        }

        applyMirror();
        render(false);

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            toggle.disabled = true;
            showStatus("Camera is not available here. Browsers allow it only on localhost or HTTPS.");
            return;
        }

        toggle.addEventListener("click", function () {
            if (stream) {
                stop(true);
            } else {
                start();
            }
        });
        mirror.addEventListener("change", function () {
            prefs.mirrored = mirror.checked;
            applyMirror();
            savePrefs(prefs);
        });
        // Turn the camera light off when leaving the page (finishing the
        // interview navigates away), without forgetting the "on" choice.
        window.addEventListener("pagehide", release);

        if (prefs.enabled) start();
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-self-view]").forEach(init);
    });
})();
