/* Opt-in interview recording (theory page). When "Record this rehearsal" is
   ticked: camera + microphone are opened through window.RehearseSelfView, a
   10-second gaze calibration is recorded (once per interview session), then
   one clip per question round is recorded from the moment the round is shown
   until the answer is submitted. Clips are uploaded to this Rehearse server
   only (data/recordings/). The on/off choice is remembered per interview
   session, so a refresh resumes recording; a new rehearsal starts off.

   interview.html drives it through window.RehearseRecording:
     roundStart({questionId, round}) - a question or follow-up is on screen
     roundEnd()                      - the answer was submitted / timed out
     flush()                         - wait for uploads before leaving the page */
(function () {
    "use strict";

    var MIME_CANDIDATES = [
        "video/webm;codecs=vp9,opus",
        "video/webm;codecs=vp8,opus",
        "video/webm",
        "video/mp4"
    ];
    var RECORDER_OPTIONS = { videoBitsPerSecond: 1000000, audioBitsPerSecond: 64000 };
    var CALIBRATION_STEPS = [
        { target: "camera", text: "Look at the camera lens", seconds: 5 },
        { target: "screen", text: "Now look at the centre of the screen", seconds: 5 }
    ];
    var FLUSH_TIMEOUT_MS = 60000;

    var root = null;
    var toggle = null;
    var indicator = null;
    var indicatorLabel = null;
    var statusEl = null;
    var interviewId = "";

    var enabled = false;
    var calibrating = false;
    var calibrated = false;
    var stream = null;
    var mimeType = "";
    var currentRound = null;
    var active = null;          // { recorder, chunks, info, startedAt, t0 }
    var pending = [];           // in-flight upload promises
    var uploadedAny = false;

    function base() {
        return "/interview/" + encodeURIComponent(interviewId) + "/recordings";
    }

    function showStatus(text) {
        if (!statusEl) return;
        statusEl.textContent = text || "";
        statusEl.hidden = !text;
    }

    function setIndicator(text) {
        if (!indicator) return;
        indicator.hidden = !text;
        if (indicatorLabel) indicatorLabel.textContent = text || "";
    }

    function pickMimeType() {
        if (!window.MediaRecorder) return null;
        for (var i = 0; i < MIME_CANDIDATES.length; i++) {
            if (MediaRecorder.isTypeSupported(MIME_CANDIDATES[i])) return MIME_CANDIDATES[i];
        }
        return "";
    }

    function newRecorder() {
        var options = Object.assign({}, RECORDER_OPTIONS);
        if (mimeType) options.mimeType = mimeType;
        return new MediaRecorder(stream, options);
    }

    // Record until stopRecording() resolves with the finished Blob.
    function startRecording() {
        var recorder = newRecorder();
        var chunks = [];
        recorder.addEventListener("dataavailable", function (event) {
            if (event.data && event.data.size > 0) chunks.push(event.data);
        });
        var done = new Promise(function (resolve) {
            recorder.addEventListener("stop", function () {
                resolve(new Blob(chunks, { type: recorder.mimeType || mimeType || "video/webm" }));
            });
        });
        recorder.start(1000);
        return { recorder: recorder, done: done, t0: performance.now(), startedAt: new Date().toISOString() };
    }

    function stopRecording(handle) {
        if (handle.recorder.state !== "inactive") handle.recorder.stop();
        return handle.done;
    }

    function track(promise) {
        pending.push(promise);
        promise.finally(function () {
            pending = pending.filter(function (item) { return item !== promise; });
        });
        return promise;
    }

    function session() {
        var selfView = window.RehearseSelfView;
        return selfView ? selfView.session : { get: function () { return {}; }, update: function () {} };
    }

    function upload(url, form, failureText) {
        return track(fetch(url, { method: "POST", body: form }).then(function (response) {
            if (!response.ok) throw new Error("HTTP " + response.status);
            uploadedAny = true;
            return true;
        }).catch(function () {
            showStatus(failureText);
            return false;
        }));
    }

    function fileName(blob) {
        return (blob.type.indexOf("mp4") >= 0) ? "clip.mp4" : "clip.webm";
    }

    function startClip(info) {
        if (!enabled || calibrating || !info || !stream) return;
        if (active && active.info.questionId === info.questionId && active.info.round === info.round) return;
        stopClip();
        var handle = startRecording();
        active = { handle: handle, info: info };
        setIndicator("Recording this answer");
    }

    function stopClip() {
        if (!active) return Promise.resolve();
        var clip = active;
        active = null;
        setIndicator(enabled ? "Recording on — waiting for the next question" : "");
        var durationMs = Math.round(performance.now() - clip.handle.t0);
        return track(stopRecording(clip.handle).then(function (blob) {
            if (blob.size === 0) return;
            var form = new FormData();
            form.append("question_id", clip.info.questionId);
            form.append("round", String(clip.info.round));
            form.append("started_at", clip.handle.startedAt);
            form.append("duration_ms", String(durationMs));
            form.append("file", blob, fileName(blob));
            return upload(base() + "/clips", form, "Could not save the recording of an answer.");
        }));
    }

    function overlay(text, count) {
        var frame = window.RehearseSelfView && window.RehearseSelfView.frame;
        var box = frame && frame.querySelector("[data-calibration-overlay]");
        if (!box) return;
        if (!text) {
            box.hidden = true;
            box.replaceChildren();
            return;
        }
        var line = document.createElement("span");
        line.textContent = text;
        var counter = document.createElement("span");
        counter.className = "self-view__overlay-count";
        counter.textContent = String(count);
        box.replaceChildren(line, counter);
        box.hidden = false;
    }

    function wait(ms) {
        return new Promise(function (resolve) { setTimeout(resolve, ms); });
    }

    // 10 s clip with known look targets, used by external gaze analysis:
    // the webcam sits above the screen, so "looking at the interviewer"
    // differs per setup and needs a personal baseline.
    async function calibrate() {
        calibrating = true;
        setIndicator("Calibrating");
        // Show the preview during calibration even if it is minimized.
        var panel = window.RehearseSelfView && window.RehearseSelfView.root;
        if (panel) panel.classList.add("self-view--calibrating");
        var handle = startRecording();
        var segments = [];
        var offset = 0;
        for (var i = 0; i < CALIBRATION_STEPS.length; i++) {
            var step = CALIBRATION_STEPS[i];
            for (var left = step.seconds; left > 0; left--) {
                if (!enabled) break;
                overlay(step.text, left);
                await wait(1000);
            }
            segments.push({ target: step.target, start_s: offset, end_s: offset + step.seconds });
            offset += step.seconds;
        }
        overlay(null);
        if (panel) panel.classList.remove("self-view--calibrating");
        var blob = await stopRecording(handle);
        calibrating = false;
        if (!enabled || blob.size === 0) return;
        calibrated = true;
        var form = new FormData();
        form.append("segments", JSON.stringify(segments));
        form.append("recorded_at", handle.startedAt);
        form.append("file", blob, fileName(blob));
        upload(base() + "/calibration", form, "Could not save the calibration clip.").then(function (ok) {
            if (ok) session().update({ calibrated: true });
        });
    }

    async function enable() {
        var selfView = window.RehearseSelfView;
        mimeType = pickMimeType();
        if (mimeType === null || !selfView) {
            toggle.checked = false;
            showStatus("Recording is not supported in this browser.");
            return;
        }
        toggle.disabled = true;
        showStatus("");
        try {
            stream = await selfView.open(true);
        } catch (error) {
            toggle.checked = false;
            toggle.disabled = false;
            return;  // self-view already explains why
        }
        enabled = true;
        toggle.disabled = false;
        session().update({ recording: true });
        calibrated = calibrated || session().get().calibrated === true;
        if (!calibrated) await calibrate();
        if (!enabled) return;
        setIndicator("Recording on — waiting for the next question");
        var info = typeof window.grillkitCurrentRound === "function" ? window.grillkitCurrentRound() : currentRound;
        startClip(info);
    }

    function disable(message) {
        enabled = false;
        toggle.checked = false;
        session().update({ recording: false });
        stopClip();
        overlay(null);
        var panel = window.RehearseSelfView && window.RehearseSelfView.root;
        if (panel) panel.classList.remove("self-view--calibrating");
        setIndicator("");
        if (message) showStatus(message);
    }

    window.RehearseRecording = {
        roundStart: function (info) {
            currentRound = info;
            startClip(info);
        },
        roundEnd: function () {
            currentRound = null;
            stopClip();
        },
        flush: function () {
            stopClip();
            var all = Promise.allSettled(pending.slice()).then(function () {
                if (!uploadedAny) return;
                // Rebuild manifest.json with the final answers.
                return fetch(base() + "/manifest.json").catch(function () { /* best effort */ });
            });
            var timeout = wait(FLUSH_TIMEOUT_MS);
            return Promise.race([all, timeout]);
        }
    };

    document.addEventListener("DOMContentLoaded", function () {
        root = document.querySelector("[data-recording]");
        if (!root) return;
        interviewId = root.getAttribute("data-interview-id") || "";
        toggle = root.querySelector("[data-recording-toggle]");
        indicator = root.querySelector("[data-recording-indicator]");
        indicatorLabel = root.querySelector("[data-recording-label]");
        statusEl = root.querySelector("[data-recording-status]");
        if (!toggle) return;

        toggle.checked = false;
        toggle.addEventListener("change", function () {
            if (toggle.checked) {
                enable();
            } else {
                disable("");
            }
        });
        document.addEventListener("rehearse:camera-off", function () {
            if (enabled) disable("Recording stopped because the camera was turned off.");
        });
        // Same interview session (e.g. after a refresh): resume recording,
        // without repeating the calibration.
        if (session().get().recording) {
            toggle.checked = true;
            enable();
        }
    });
})();
