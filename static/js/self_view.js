/* Camera self-view for interview pages (templates/_self_view.html).
   The camera is always off when a page loads; only the mirror choice is
   remembered. The preview is video only. When recording is switched on
   (static/js/recording.js) the stream is re-opened with the microphone too,
   through window.RehearseSelfView. Nothing here uploads anything. */
(function () {
    "use strict";

    var STORAGE_KEY = "rehearse-self-view";
    var PREVIEW_VIDEO = { width: { ideal: 640 }, height: { ideal: 360 }, facingMode: "user" };
    var RECORDING_VIDEO = { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" };

    function loadMirrored() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (raw) return JSON.parse(raw).mirrored !== false;
        } catch (e) { /* storage blocked: keep default */ }
        return true;
    }

    function saveMirrored(mirrored) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ mirrored: mirrored })); } catch (e) { /* ignore */ }
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
        if (!toggle || !frame || !video || !mirror || !status) return null;

        var mirrored = loadMirrored();
        var stream = null;
        var pending = null;

        function showStatus(text) {
            status.textContent = text || "";
            status.hidden = !text;
        }

        function applyMirror() {
            mirror.checked = mirrored;
            video.classList.toggle("self-view__video--mirrored", mirrored);
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

        function stop() {
            var wasOn = !!stream;
            release();
            render(false);
            if (wasOn) root.dispatchEvent(new CustomEvent("rehearse:camera-off", { bubbles: true }));
        }

        function hasAudio() {
            return !!stream && stream.getAudioTracks().length > 0;
        }

        // Open (or re-open) the camera. withAudio adds the microphone and a
        // higher resolution for recording. Concurrent callers share one request.
        function open(withAudio) {
            if (stream && (!withAudio || hasAudio())) return Promise.resolve(stream);
            if (pending) return pending;
            toggle.disabled = true;
            showStatus("");
            pending = navigator.mediaDevices.getUserMedia({
                video: withAudio ? RECORDING_VIDEO : PREVIEW_VIDEO,
                audio: withAudio
                    ? { echoCancellation: true, noiseSuppression: true }
                    : false
            }).then(function (media) {
                release();
                stream = media;
                video.srcObject = media;
                media.getVideoTracks().forEach(function (track) {
                    // Camera unplugged or taken by the OS mid-interview.
                    track.addEventListener("ended", function () {
                        if (stream !== media) return;
                        stop();
                        showStatus("The camera stopped.");
                    });
                });
                render(true);
                return media;
            }).catch(function (error) {
                if (!stream) render(false);
                showStatus(errorMessage(error));
                throw error;
            }).finally(function () {
                pending = null;
                toggle.disabled = false;
            });
            return pending;
        }

        applyMirror();
        render(false);

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            toggle.disabled = true;
            showStatus("Camera is not available here. Browsers allow it only on localhost or HTTPS.");
            return null;
        }

        toggle.addEventListener("click", function () {
            if (stream) {
                stop();
            } else {
                open(false).catch(function () { /* message already shown */ });
            }
        });
        mirror.addEventListener("change", function () {
            mirrored = mirror.checked;
            applyMirror();
            saveMirrored(mirrored);
        });
        // Turn the camera light off when leaving the page.
        window.addEventListener("pagehide", release);

        return {
            root: root,
            frame: frame,
            open: open,
            stop: stop,
            isOn: function () { return !!stream; },
            showStatus: showStatus
        };
    }

    document.addEventListener("DOMContentLoaded", function () {
        var api = null;
        document.querySelectorAll("[data-self-view]").forEach(function (root) {
            var instance = init(root);
            if (!api && instance) api = instance;
        });
        // One self-view per page; recording.js drives it through this API.
        window.RehearseSelfView = api;
        document.dispatchEvent(new CustomEvent("rehearse:self-view-ready"));
    });
})();
