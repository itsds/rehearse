/* Progress trend charts: crosshair that snaps to the nearest rehearsal,
   a tooltip with its numbers, and click-anywhere to open that rehearsal.
   The SVG itself is server-rendered (templates/_trend_chart.html). */
(function () {
    "use strict";

    function addRow(parent, text, className) {
        var row = document.createElement("div");
        if (className) row.className = className;
        row.textContent = text;
        parent.appendChild(row);
    }

    function fillTooltip(tooltip, point) {
        var d = point.dataset;
        tooltip.replaceChildren();
        addRow(tooltip, d.date, "trend-chart__tooltip-date");
        addRow(tooltip, d.title, "trend-chart__tooltip-title");
        addRow(tooltip, "First-answer avg " + d.average + " / 5", "trend-chart__tooltip-value");
        var details = d.questions + (d.questions === "1" ? " question" : " questions");
        details += " · " + d.followUps + (d.followUps === "1" ? " follow-up" : " follow-ups");
        if (d.timedOut !== "0") details += " · " + d.timedOut + " timed out";
        addRow(tooltip, details);
        if (d.percent) addRow(tooltip, "Session score " + d.percent + "%");
    }

    function initChart(figure) {
        var svg = figure.querySelector("svg");
        var crosshair = figure.querySelector("[data-crosshair]");
        var tooltip = figure.querySelector("[data-tooltip]");
        var points = Array.prototype.slice.call(figure.querySelectorAll(".trend-chart__point"));
        if (!svg || !crosshair || !tooltip || points.length === 0) return;
        var active = null;

        // The SVG scales with its container; counter-scale text and dots
        // (via a CSS variable) so they stay readable on phones and big screens.
        var viewWidth = parseFloat(figure.dataset.viewWidth);
        function fit() {
            var rendered = svg.getBoundingClientRect().width;
            if (rendered > 0 && viewWidth > 0) {
                figure.style.setProperty("--trend-scale", String(viewWidth / rendered));
            }
        }
        // Hide date labels that would collide on narrow charts; the first and
        // last label always stay so the time span is readable.
        var dateLabels = Array.prototype.slice.call(figure.querySelectorAll(".trend-chart__axis--x"));
        function declutter() {
            dateLabels.forEach(function (label) { label.style.visibility = ""; });
            var gap = 6;
            var last = dateLabels[dateLabels.length - 1];
            var prevRight = -Infinity;
            dateLabels.forEach(function (label, index) {
                var rect = label.getBoundingClientRect();
                var lastRect = last.getBoundingClientRect();
                var isEdge = index === 0 || label === last;
                var collides = rect.left < prevRight + gap
                    || (!isEdge && rect.right + gap > lastRect.left);
                if (collides && !isEdge) {
                    label.style.visibility = "hidden";
                } else {
                    prevRight = rect.right;
                }
            });
        }
        function refresh() {
            fit();
            if (dateLabels.length > 2) declutter();
        }
        refresh();
        if (window.ResizeObserver) new ResizeObserver(refresh).observe(svg);

        function show(point) {
            if (active && active !== point) active.classList.remove("is-active");
            active = point;
            point.classList.add("is-active");
            var x = point.dataset.x;
            crosshair.setAttribute("x1", x);
            crosshair.setAttribute("x2", x);
            crosshair.classList.add("is-visible");
            fillTooltip(tooltip, point);
            tooltip.hidden = false;

            var box = figure.getBoundingClientRect();
            var dot = point.querySelector("circle").getBoundingClientRect();
            var left = dot.left - box.left + dot.width / 2;
            var top = dot.top - box.top;
            // Keep the tooltip inside the figure horizontally.
            var half = tooltip.offsetWidth / 2;
            left = Math.max(half, Math.min(box.width - half, left));
            tooltip.style.left = left + "px";
            tooltip.style.top = top + "px";
        }

        function hide() {
            if (active) active.classList.remove("is-active");
            active = null;
            crosshair.classList.remove("is-visible");
            tooltip.hidden = true;
        }

        function nearest(event) {
            var matrix = svg.getScreenCTM();
            if (!matrix) return null;
            var pt = svg.createSVGPoint();
            pt.x = event.clientX;
            pt.y = event.clientY;
            var x = pt.matrixTransform(matrix.inverse()).x;
            var best = null;
            var bestDistance = Infinity;
            points.forEach(function (point) {
                var distance = Math.abs(parseFloat(point.dataset.x) - x);
                if (distance < bestDistance) {
                    best = point;
                    bestDistance = distance;
                }
            });
            return best;
        }

        svg.addEventListener("pointermove", function (event) {
            var point = nearest(event);
            if (point) show(point);
        });
        svg.addEventListener("pointerleave", hide);
        svg.addEventListener("click", function (event) {
            if (event.target.closest(".trend-chart__point")) return;
            var point = nearest(event);
            if (point) window.location.href = point.getAttribute("href");
        });
        points.forEach(function (point) {
            point.addEventListener("focus", function () { show(point); });
            point.addEventListener("blur", hide);
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-trend-chart]").forEach(initChart);
    });
})();
