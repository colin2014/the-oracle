/* ═══════════════════════════════════════════════════════════════
   Dynamic page modules — engine
   ───────────────────────────────────────────────────────────────
   Mounts an interactive "run it" module underneath a reading page.

   The shell here is topic-agnostic: stage frame, run/step/reset,
   speed, narration, trace log, readout panels, and the markscheme
   payoff. Each topic module supplies its own SVG stage and a
   generator that yields one step per tick.

   Registration:
       DynamicPage.register('A1.1.1', { ...definition... });
       DynamicPage.register(['A1.1.1','A1.1.5'], def);   // shared

   Mounting (called by book_page.html after content renders):
       DynamicPage.mount(hostElement, 'A1.1.1');

   Modules are lazy-loaded from /static/js/dynamic/ via the MODULES
   map, so a page only downloads the module it actually uses.

   Element lookup is scoped with [data-el="name"] rather than ids,
   because reading mode renders every page of a book into a single
   document — ids would collide across mounted modules.
   ═══════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    var SVGNS = 'http://www.w3.org/2000/svg';
    var BASE = (function () {
        var s = document.currentScript;
        return s ? new URL('.', s.src).href : '/static/js/';
    })();

    var ICON = {
        play: '<polygon points="5 3 19 12 5 21 5 3"/>',
        pause: '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>',
        step: '<polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19"/>',
        reset: '<polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>',
        check: '<polyline points="20 6 9 17 4 12"/>',
        expand: '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>',
        close: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
        list: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
        code: '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
        clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'
    };

    function svgIcon(name, size, width) {
        return '<svg width="' + (size || 15) + '" height="' + (size || 15) + '" viewBox="0 0 24 24" ' +
            'fill="none" stroke="currentColor" stroke-width="' + (width || 2) + '" ' +
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[name] + '</svg>';
    }

    function reduced() {
        return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }

    function easeInOut(t) {
        return t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    var registry = {};   // topic -> definition
    var loading = {};    // file -> Promise

    /* ── lazy module loading ────────────────────────────────── */

    var MODULES = {
        'A1.1.5': 'a1-1-5-fde.js'
    };

    function loadModule(topic) {
        if (registry[topic]) return Promise.resolve(registry[topic]);
        var file = MODULES[topic];
        if (!file) return Promise.resolve(null);
        if (!loading[file]) {
            loading[file] = new Promise(function (resolve, reject) {
                var s = document.createElement('script');
                s.src = BASE + 'dynamic/' + file;
                s.onload = resolve;
                s.onerror = function () { reject(new Error('Failed to load module ' + file)); };
                document.head.appendChild(s);
            });
        }
        return loading[file].then(function () { return registry[topic] || null; });
    }

    /* ── shell markup ───────────────────────────────────────── */

    function buildShell(def) {
        var el = document.createElement('section');
        el.className = 'dp-module';

        var panels = (def.panels || []).map(function (p) {
            if (p.key === 'stats') {
                return '<div class="dp-panel"><div class="dp-panel-h">' + svgIcon('clock', 13) +
                    (p.title || 'This run') + '</div><div>' +
                    (p.stats || []).map(function (s) {
                        return '<div class="dp-stat">' +
                            '<div class="dp-stat-k">' + s.label + '</div>' +
                            '<div class="dp-stat-v" data-el="stat-' + s.key + '">' + (s.initial || '0') + '</div>' +
                            '<div class="dp-stat-n" data-el="statnote-' + s.key + '">' + (s.note || '') + '</div>' +
                            '</div>';
                    }).join('') + '</div></div>';
            }
            var icon = p.key === 'log' ? 'list' : 'code';
            return '<div class="dp-panel"><div class="dp-panel-h">' + svgIcon(icon, 13) + (p.title || '') +
                (p.key === 'log' ? '<span class="dp-count" data-el="log-count"></span>' : '') +
                '</div><div class="dp-panel-b">' +
                '<div data-el="panel-' + p.key + '">' +
                (p.key === 'log' ? '<div class="dp-empty">Nothing has run yet.</div>' : '') +
                '</div>' +
                (p.note ? '<p class="dp-panel-note">' + p.note + '</p>' : '') +
                '</div></div>';
        }).join('');

        var marks = def.marks ? ('<div class="dp-payoff">' +
            '<h4>' + def.marks.title + '</h4>' +
            '<p class="dp-lead">' + def.marks.lead + '</p>' +
            '<div class="dp-marks">' +
            def.marks.items.map(function (m) {
                return '<div class="dp-mark" data-el="mark-' + m.id + '">' +
                    '<span class="dp-tick">' + svgIcon('check', 13, 3) + '</span>' +
                    '<div><div class="dp-mark-t">' + m.t + '</div>' +
                    '<div class="dp-mark-d">' + m.d + '</div>' +
                    '<div class="dp-mark-cy" data-el="markcy-' + m.id + '"></div></div></div>';
            }).join('') +
            '</div></div>') : '';

        el.innerHTML =
            '<div class="dp-head">' +
            '<div class="dp-head-txt"><h3>' + def.heading + '</h3><p>' + def.intro + '</p></div>' +
            '<button class="dp-btn dp-btn-ghost dp-expand" data-el="expand" ' +
            'title="Open full screen so the diagram and the trace fit side by side">' +
            svgIcon('expand') + '<span data-el="expand-label">Full screen</span></button>' +
            '</div>' +
            '<div class="dp-stage-wrap">' + def.stage + '</div>' +
            '<div class="dp-side">' +
            '<div class="dp-narration" aria-live="polite">' +
            '<div class="dp-phase">' +
            '<span class="dp-phase-name" data-el="phase">READY</span>' +
            '<span class="dp-phase-n" data-el="phase-n">' + (def.unit || 'step') + ' 0</span>' +
            '</div>' +
            '<div class="dp-narr-wrap">' +
            '<div class="dp-narr-label">What\'s happening</div>' +
            '<div class="dp-narr" data-el="narration"></div>' +
            '</div>' +
            '</div>' +
            '<div class="dp-controls">' +
            '<button class="dp-btn dp-btn-primary" data-el="run">' + svgIcon('play') +
            '<span data-el="run-label">Run</span></button>' +
            '<button class="dp-btn dp-btn-ghost" data-el="step">' + svgIcon('step') +
            (def.stepLabel || 'Step once') + '</button>' +
            '<button class="dp-btn dp-btn-ghost" data-el="reset">' + svgIcon('reset') + 'Reset</button>' +
            '<span class="dp-spacer"></span>' +
            '<span class="dp-seg-label">Speed</span>' +
            '<div class="dp-seg" role="group" aria-label="Playback speed">' +
            '<button data-speed="1.7" aria-pressed="false">Slow</button>' +
            '<button data-speed="1" aria-pressed="true">Normal</button>' +
            '<button data-speed="0.45" aria-pressed="false">Fast</button>' +
            '</div></div>' +
            (panels ? '<div class="dp-readouts">' + panels + '</div>' : '') +
            marks +
            '<p class="dp-closing" data-el="closing"></p>' +
            '</div>';

        return el;
    }

    /* ── the runtime handed to each module ──────────────────── */

    function makeContext(root, def) {
        var ctx = {
            root: root,
            def: def,
            state: {},
            speed: 1,
            n: 0,
            reduced: reduced,

            $: function (name) { return root.querySelector('[data-el="' + name + '"]'); },
            $$: function (name) { return Array.prototype.slice.call(root.querySelectorAll('[data-el="' + name + '"]')); },
            svg: function () { return root.querySelector('.dp-stage'); },

            D: function (ms) { return ms * ctx.speed; },
            wait: function (ms) {
                var d = reduced() ? Math.min(ms, 60) : ms;
                return new Promise(function (r) { setTimeout(r, d); });
            },

            /* value slot: set text and flash the box */
            setVal: function (name, value) {
                var t = ctx.$('v-' + name), b = ctx.$('slot-' + name);
                if (t) t.textContent = (value === null || value === undefined) ? '—' : String(value);
                if (b) {
                    b.classList.remove('is-changed');
                    void b.getBoundingClientRect().width;
                    b.classList.add('is-changed');
                }
            },

            activate: function () {
                Array.prototype.forEach.call(arguments, function (name) {
                    var e = ctx.$(name);
                    if (e) e.classList.add('is-active');
                });
            },
            hot: function () {
                Array.prototype.forEach.call(arguments, function (name) {
                    var e = ctx.$(name);
                    if (e) e.classList.add('is-hot');
                });
            },
            mark: function (name, kind) {           // 'is-hit' / 'is-miss'
                var e = ctx.$(name);
                if (e) e.classList.add(kind);
            },
            badge: function (name, txt, kind) {
                var b = ctx.$('badge-' + name);
                if (!b) return;
                b.textContent = txt;
                b.setAttribute('fill', kind === 'hit' ? 'var(--success)' : 'var(--warning)');
                b.setAttribute('opacity', '1');
            },
            clear: function () {
                ['is-active', 'is-hot', 'is-hit', 'is-miss'].forEach(function (c) {
                    Array.prototype.forEach.call(root.querySelectorAll('.' + c), function (e) {
                        e.classList.remove(c);
                    });
                });
                Array.prototype.forEach.call(root.querySelectorAll('.dp-badge'), function (b) {
                    b.setAttribute('opacity', '0');
                });
                Array.prototype.forEach.call(root.querySelectorAll('.dp-wave'), function (w) {
                    w.classList.remove('is-ticking');
                });
            },

            narrate: function (html, note) {
                var el = ctx.$('narration');
                if (el) el.innerHTML = html + (note ? '<span class="dp-note">' + note + '</span>' : '');
            },
            setPhase: function (name, n) {
                var p = ctx.$('phase'), q = ctx.$('phase-n');
                if (p) p.textContent = name;
                if (q) q.textContent = (def.unit || 'step') + ' ' + n;
            },
            stat: function (key, value, note) {
                var v = ctx.$('stat-' + key), nEl = ctx.$('statnote-' + key);
                if (v) v.textContent = String(value);
                if (nEl && note !== undefined) nEl.textContent = note;
            },
            log: function (n, phase, op, plain) {
                var box = ctx.$('panel-log');
                if (!box) return;
                var empty = box.querySelector('.dp-empty');
                if (empty) empty.remove();
                Array.prototype.forEach.call(box.querySelectorAll('.is-now'), function (r) {
                    r.classList.remove('is-now');
                });
                var d = document.createElement('div');
                d.className = 'dp-log-row is-now';
                d.innerHTML = '<span class="dp-c">' + n + '</span><span class="dp-t"></span>';
                d.querySelector('.dp-t').textContent = op;
                if (plain) d.title = plain;
                box.appendChild(d);
                var scroller = box.closest('.dp-panel-b');
                if (scroller) scroller.scrollTop = scroller.scrollHeight;
                var c = ctx.$('log-count');
                if (c) c.textContent = n + ' ' + (def.unit || 'step') + (n === 1 ? '' : 's');
            },
            earn: function (id, n) {
                var box = ctx.$('mark-' + id);
                if (!box || box.classList.contains('is-earned')) return;
                box.classList.add('is-earned');
                var cy = ctx.$('markcy-' + id);
                if (cy) cy.textContent = 'first shown at ' + (def.unit || 'step') + ' ' + n;
            },

            /* Move a labelled packet along an SVG path. Geometry only —
               the path itself is never rendered. */
            move: function (d, label, dur, kind) {
                return new Promise(function (res) {
                    if (reduced()) { setTimeout(res, 90); return; }
                    var host = ctx.$('packets'), gauge = ctx.$('measure');
                    if (!host || !gauge) { setTimeout(res, dur); return; }
                    var p = document.createElementNS(SVGNS, 'path');
                    p.setAttribute('d', d);
                    gauge.appendChild(p);
                    var len = p.getTotalLength();
                    var fill = kind === 'ctl' ? 'var(--primary)'
                        : kind === 'addr' ? 'var(--info)' : 'var(--success)';
                    var g = document.createElementNS(SVGNS, 'g');
                    var w = Math.max(38, String(label).length * 8.2 + 16);
                    g.innerHTML =
                        '<rect x="' + (-w / 2) + '" y="-13" width="' + w + '" height="26" rx="7" ' +
                        'fill="var(--bg-white)" stroke="' + fill + '" stroke-width="1.5"/>' +
                        '<text class="dp-packet-txt" fill="' + fill + '"></text>';
                    g.querySelector('text').textContent = label;
                    host.appendChild(g);
                    var t0 = performance.now();
                    (function frame(now) {
                        var k = Math.min(1, (now - t0) / dur);
                        var pt = p.getPointAtLength(easeInOut(k) * len);
                        g.setAttribute('transform', 'translate(' + pt.x + ',' + pt.y + ')');
                        g.setAttribute('opacity', k < .08 ? String(k / .08) : k > .92 ? String((1 - k) / .08) : '1');
                        if (k < 1) requestAnimationFrame(frame);
                        else { g.remove(); p.remove(); res(); }
                    })(t0);
                });
            }
        };
        return ctx;
    }

    /* ── the run loop ───────────────────────────────────────── */

    function wire(root, def) {
        var ctx = makeContext(root, def);
        var gen = null, running = false, busy = false, done = false;

        function fullReset() {
            running = false; busy = false; done = false;
            ctx.n = 0;
            ctx.clear();
            if (def.reset) def.reset(ctx);
            gen = def.steps(ctx);
            var logBox = ctx.$('panel-log');
            if (logBox) logBox.innerHTML = '<div class="dp-empty">Nothing has run yet.</div>';
            var lc = ctx.$('log-count'); if (lc) lc.textContent = '';
            (def.marks ? def.marks.items : []).forEach(function (m) {
                var b = ctx.$('mark-' + m.id); if (b) b.classList.remove('is-earned');
                var c = ctx.$('markcy-' + m.id); if (c) c.textContent = '';
            });
            var closing = ctx.$('closing'); if (closing) closing.innerHTML = '';
            ctx.setPhase('READY', 0);
            ctx.$('run-label').textContent = 'Run';
            ctx.$('run').innerHTML = svgIcon('play') + '<span data-el="run-label">Run</span>';
            ctx.$('step').disabled = false;
            ctx.$('run').disabled = false;
        }

        function finish() {
            running = false; done = true;
            ctx.clear();
            ctx.$('step').disabled = true;
            ctx.$('run').disabled = true;
            ctx.$('run').innerHTML = svgIcon('play') + '<span data-el="run-label">Run</span>';
            ctx.setPhase('DONE', ctx.n);
            if (def.finish) {
                var html = def.finish(ctx);
                var el = ctx.$('closing');
                if (el && html) el.innerHTML = html;
            }
        }

        function stepOnce() {
            if (busy || done) return Promise.resolve(false);
            var next = gen.next();
            if (next.done || !next.value) { finish(); return Promise.resolve(false); }
            busy = true;
            var st = next.value;
            ctx.clear();
            ctx.n++;
            Array.prototype.forEach.call(root.querySelectorAll('.dp-wave'), function (w) {
                w.classList.add('is-ticking');
            });
            ctx.setPhase(st.phase, ctx.n);
            ctx.narrate(st.plain);
            ctx.log(ctx.n, st.phase, st.op, st.plain);
            if (st.mark) ctx.earn(st.mark, ctx.n);
            return Promise.resolve(st.run ? st.run() : null)
                .catch(function () { /* never let one step wedge the module */ })
                .then(function () {
                    if (def.afterStep) def.afterStep(ctx);
                    busy = false;
                    if (ctx.state.halted) { finish(); return false; }
                    return true;
                });
        }

        function runLoop() {
            if (!running) return;
            stepOnce().then(function (more) {
                if (!more || !running) return;
                ctx.wait(ctx.D(420)).then(runLoop);
            });
        }

        ctx.$('step').addEventListener('click', function () {
            running = false;
            ctx.$('run').innerHTML = svgIcon('play') + '<span data-el="run-label">Run</span>';
            stepOnce();
        });
        ctx.$('run').addEventListener('click', function () {
            if (running) {
                running = false;
                ctx.$('run').innerHTML = svgIcon('play') + '<span data-el="run-label">Run</span>';
                return;
            }
            running = true;
            ctx.$('run').innerHTML = svgIcon('pause') + '<span data-el="run-label">Pause</span>';
            runLoop();
        });
        ctx.$('reset').addEventListener('click', fullReset);

        /* ── full screen ────────────────────────────────────
           The stage and the trace cannot both be read at once in a
           page column, so this lifts the module into an overlay and
           puts them side by side. The module element itself is MOVED,
           not rebuilt, so a run in progress keeps its state. */
        var home = null, overlay = null;

        function onKey(e) { if (e.key === 'Escape') exitFS(); }

        function enterFS() {
            if (overlay) return;
            home = { parent: root.parentNode, next: root.nextSibling };
            overlay = document.createElement('div');
            overlay.className = 'dp-overlay';
            document.body.appendChild(overlay);
            overlay.appendChild(root);
            root.classList.add('dp-fs');
            document.documentElement.style.overflow = 'hidden';
            ctx.$('expand').innerHTML = svgIcon('close') + '<span data-el="expand-label">Close</span>';
            document.addEventListener('keydown', onKey);
            ctx.$('expand').focus();
        }

        function exitFS() {
            if (!overlay) return;
            root.classList.remove('dp-fs');
            if (home.parent) home.parent.insertBefore(root, home.next);
            overlay.remove();
            overlay = null;
            document.documentElement.style.overflow = '';
            ctx.$('expand').innerHTML = svgIcon('expand') + '<span data-el="expand-label">Full screen</span>';
            document.removeEventListener('keydown', onKey);
        }

        ctx.$('expand').addEventListener('click', function () {
            if (overlay) exitFS(); else enterFS();
        });

        root.querySelectorAll('.dp-seg button').forEach(function (b) {
            b.addEventListener('click', function () {
                root.querySelectorAll('.dp-seg button').forEach(function (x) {
                    x.setAttribute('aria-pressed', 'false');
                });
                b.setAttribute('aria-pressed', 'true');
                ctx.speed = parseFloat(b.dataset.speed);
            });
        });

        /* Pause anything running once the module scrolls out of view — but not
           while it is in the overlay, where moving the element between parents
           briefly reads as "not intersecting". */
        if ('IntersectionObserver' in window) {
            new IntersectionObserver(function (entries) {
                entries.forEach(function (e) {
                    if (!overlay && !e.isIntersecting && running) {
                        running = false;
                        ctx.$('run').innerHTML = svgIcon('play') + '<span data-el="run-label">Run</span>';
                    }
                });
            }, { threshold: 0 }).observe(root);
        }

        if (def.init) def.init(ctx);
        fullReset();
        return ctx;
    }

    /* ── public API ─────────────────────────────────────────── */

    var DynamicPage = {
        MODULES: MODULES,
        icon: svgIcon,

        register: function (topics, def) {
            (Array.isArray(topics) ? topics : [topics]).forEach(function (t) {
                registry[t] = Object.assign({}, def, (def.variants && def.variants[t]) || {});
            });
        },

        has: function (topic) { return !!MODULES[topic]; },

        /** Mount the module for `topic` at the end of `host`. Resolves to
         *  the module element, or null when the topic has no module. */
        mount: function (host, topic) {
            if (!host || !topic) return Promise.resolve(null);
            topic = String(topic).trim();
            var existing = host.querySelector('.dp-module[data-topic="' + topic + '"]');
            if (existing) return Promise.resolve(existing);

            return loadModule(topic).then(function (def) {
                if (!def) return null;
                if (host.querySelector('.dp-module[data-topic="' + topic + '"]')) return null;
                var el = buildShell(def);
                el.setAttribute('data-topic', topic);
                host.appendChild(el);
                try {
                    wire(el, def);
                } catch (err) {
                    console.error('[DynamicPage] module ' + topic + ' failed to start', err);
                    el.remove();
                    return null;
                }
                return el;
            }).catch(function (err) {
                console.error('[DynamicPage] could not load module for ' + topic, err);
                return null;
            });
        }
    };

    window.DynamicPage = DynamicPage;
})();
