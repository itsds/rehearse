/* Camera self-view for interview pages (templates/_self_view.html).

   Camera on/off, recording on/off and the preview size are remembered per
   interview session (keyed by interview id): a new rehearsal always starts
   with the camera off, while refreshing or returning to the same rehearsal
   restores what you had. The mirror choice is a global preference.
   Recording (static/js/recording.js) re-opens the same stream with the
   microphone through window.RehearseSelfView. Nothing here uploads anything. */
(function () {
    "use strict";

    var MIRROR_KEY = "rehearse-self-view";
    var SESSIONS_KEY = "rehearse-session-media";
    var SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;
    var MAX_SESSIONS = 50;
    var SIZES = ["min", "normal", "max"];
    var PREVIEW_VIDEO = { width: { ideal: 640 }, height: { ideal: 360 }, facingMode: "user" };
    var RECORDING_VIDEO = { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" };

    // ---- Per-session state: { camera, recording, calibrated, size, updated } ----

    function readSessions() {
        try {
            var raw = localStorage.getItem(SESSIONS_KEY);
            var parsed = raw ? JSON.parse(raw) : {};
            return parsed && typeof parsed === "object" ? parsed : {};
        } catch (e) {
            return {};
        }
    }

    function writeSessions(sessions) {
        // Drop old sessions so the store does not grow forever.
        var now = Date.now();
        var ids = Object.keys(sessions)
            .filter(function (id) { return now - (sessions[id].updated || 0) < SESSION_TTL_MS; })
            .sort(function (a, b) { return (sessions[b].updated || 0) - (sessions[a].updated || 0); })
            .slice(0, MAX_SESSIONS);
        var kept = {};
        ids.forEach(function (id) { kept[id] = sessions[id]; });
        try { localStorage.setItem(SESSIONS_KEY, JSON.stringify(kept)); } catch (e) { /* ignore */ }
    }

    function sessionStore(interviewId) {
        return {
            get: function () {
                var state = interviewId ? readSessions()[interviewId] : null;
                return Object.assign(
                    { camera: false, recording: false, calibrated: false, size: "normal" },
                    state || {}
                );
            },
            update: function (patch) {
                if (!interviewId) return;
                var sessions = readSessions();
                sessions[interviewId] = Object.assign(
                    {}, sessions[interviewId] || {}, patch, { updated: Date.now() }
                );
                writeSessions(sessions);
            }
        };
    }

    function loadMirrored() {
        try {
            var raw = localStorage.getItem(MIRROR_KEY);
            if (raw) return JSON.parse(raw).mirrored !== false;
        } catch (e) { /* storage blocked: keep default */ }
        return true;
    }

    function saveMirrored(mirrored) {
        try { localStorage.setItem(MIRROR_KEY, JSON.stringify({ mirrored: mirrored })); } catch (e) { /* ignore */ }
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
        var sizeBar = root.querySelector("[data-self-view-sizes]");
        var popoutBtn = root.querySelector("[data-self-view-popout]");
        if (!toggle || !frame || !video || !mirror || !status) return null;

        var store = sessionStore(root.getAttribute("data-interview-id") || "");
        var mirrored = loadMirrored();
        var size = SIZES.indexOf(store.get().size) >= 0 ? store.get().size : "normal";
        var stream = null;
        var pending = null;
        var pendingAudio = false;

        function showStatus(text) {
            status.textContent = text || "";
            status.hidden = !text;
        }

        function applyMirror() {
            mirror.checked = mirrored;
            video.classList.toggle("self-view__video--mirrored", mirrored);
        }

        function applySize() {
            SIZES.forEach(function (name) {
                root.classList.toggle("self-view--" + name, name === size);
            });
            if (!sizeBar) return;
            sizeBar.querySelectorAll("[data-self-view-size]").forEach(function (button) {
                button.setAttribute(
                    "aria-pressed",
                    button.getAttribute("data-self-view-size") === size ? "true" : "false"
                );
            });
        }

        function setSize(next) {
            if (SIZES.indexOf(next) < 0) return;
            size = next;
            applySize();
            store.update({ size: size });
        }

        function render(on) {
            toggle.textContent = on ? "Camera off" : "Camera on";
            toggle.setAttribute("aria-pressed", on ? "true" : "false");
            frame.hidden = !on;
            mirrorRow.hidden = !on;
            if (sizeBar) sizeBar.hidden = !on;
            root.classList.toggle("self-view--on", on);
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
            if (document.pictureInPictureElement === video) {
                document.exitPictureInPicture().catch(function () { /* ignore */ });
            }
            store.update({ camera: false, recording: false });
            if (wasOn) root.dispatchEvent(new CustomEvent("rehearse:camera-off", { bubbles: true }));
        }

        function hasAudio() {
            return !!stream && stream.getAudioTracks().length > 0;
        }

        // Open (or re-open) the camera. withAudio adds the microphone and a
        // higher resolution for recording. Concurrent callers share a request.
        function open(withAudio) {
            if (stream && (!withAudio || hasAudio())) return Promise.resolve(stream);
            if (pending) {
                if (!withAudio || pendingAudio) return pending;
                return pending.catch(function () { return null; }).then(function () { return open(true); });
            }
            toggle.disabled = true;
            showStatus("");
            pendingAudio = withAudio;
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
                store.update({ camera: true });
                return media;
            }).catch(function (error) {
                if (!stream) {
                    render(false);
                    store.update({ camera: false, recording: false });
                }
                showStatus(errorMessage(error));
                throw error;
            }).finally(function () {
                pending = null;
                pendingAudio = false;
                toggle.disabled = false;
            });
            return pending;
        }

        applyMirror();
        applySize();
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
        root.querySelectorAll("[data-self-view-size]").forEach(function (button) {
            button.addEventListener("click", function () {
                setSize(button.getAttribute("data-self-view-size"));
            });
        });
        if (popoutBtn) {
            // Browser picture-in-picture: a movable, resizable window that stays
            // on top of other apps. Not available in every browser.
            if (document.pictureInPictureEnabled) {
                popoutBtn.hidden = false;
                popoutBtn.addEventListener("click", function () {
                    if (document.pictureInPictureElement === video) {
                        document.exitPictureInPicture().catch(function () { /* ignore */ });
                    } else if (stream) {
                        video.requestPictureInPicture().catch(function () {
                            showStatus("Could not open the pop-out window.");
                        });
                    }
                });
            } else {
                popoutBtn.hidden = true;
            }
        }
        // Turn the camera light off when leaving the page; the per-session
        // "camera on" state is kept, so a refresh brings it back.
        window.addEventListener("pagehide", release);

        var api = {
            root: root,
            frame: frame,
            open: open,
            stop: stop,
            isOn: function () { return !!stream; },
            showStatus: showStatus,
            session: store
        };

        // Restore this session's camera. When recording was on, recording.js
        // re-opens it with the microphone instead.
        var saved = store.get();
        if (saved.camera && !(saved.recording && root.querySelector("[data-recording]"))) {
            open(false).catch(function () { /* message already shown */ });
        }
        return api;
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
