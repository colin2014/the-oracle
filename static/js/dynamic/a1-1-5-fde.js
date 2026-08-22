/* ═══════════════════════════════════════════════════════════════
   A1.1.5 — fetch, decode and execute cycle
   ───────────────────────────────────────────────────────────────
   A tiny program runs through a real CPU: values travel between
   registers, memory reads walk the cache hierarchy, and the ALU
   does the arithmetic.

       0x00  LDA 0x10        0x10 = 3
       0x01  ADD 0x11        0x11 = 4
       0x02  ADD 0x11        0x12 = result
       0x03  STA 0x12
       0x04  HLT

   The second ADD re-reads 0x11, which by then is still in L1 —
   the one genuine cache hit in the run. Nothing is faked: the
   caches are modelled with real capacities and LRU eviction and
   report whatever actually happens.

   The payoff panel maps the steps onto this topic's OWN published
   markscheme (A1.1.5 Q1: the role of the Program Counter), read
   from its content.json. Marks are never invented here.
   ═══════════════════════════════════════════════════════════════ */
(function () {
    'use strict';

    /* ── geometry (viewBox units) ───────────────────────────── */
    var RX = 396, RW = 124, RH = 44, RCX = RX + RW / 2;   // register value box
    var SPINE = 256, ALUX = 206, RAMX = 958;
    var LX = { L1: 644, L2: 764, L3: 884 };
    var CAPS = { L1: 2, L2: 4, L3: 6 };
    var CGEO = {
        L1: { x: 596, y: 262, w: 96, h: 76 },
        L2: { x: 716, y: 238, w: 96, h: 124 },
        L3: { x: 836, y: 214, w: 96, h: 172 }
    };
    var REGS = [
        { k: 'PC', y: 132, desc: 'next instruction address' },
        { k: 'IR', y: 216, desc: 'current instruction' },
        { k: 'MAR', y: 300, desc: 'address to access' },
        { k: 'MDR', y: 384, desc: 'data in transit' },
        { k: 'ACC', y: 468, desc: 'result of ALU work' }
    ];

    var PROGRAM = [
        { addr: 0x00, op: 'LDA', operand: 0x10 },
        { addr: 0x01, op: 'ADD', operand: 0x11 },
        { addr: 0x02, op: 'ADD', operand: 0x11 },
        { addr: 0x03, op: 'STA', operand: 0x12 },
        { addr: 0x04, op: 'HLT', operand: null }
    ];
    var DATA = [{ addr: 0x10, value: 3 }, { addr: 0x11, value: 4 }, { addr: 0x12, value: 0 }];

    function hex(n) { return '0x' + n.toString(16).toUpperCase().padStart(2, '0'); }
    function itext(i) { return i.op + (i.operand === null ? '' : ' ' + hex(i.operand)); }

    /* ── stage markup ───────────────────────────────────────── */
    function regRows() {
        return REGS.map(function (r) {
            return '<g>' +
                '<text class="dp-slot-name" x="290" y="' + (r.y - 4) + '">' + r.k + '</text>' +
                '<text class="dp-slot-desc" x="290" y="' + (r.y + 12) + '">' + r.desc + '</text>' +
                '<rect class="dp-slot" data-el="slot-' + r.k + '" x="' + RX + '" y="' + (r.y - RH / 2) +
                '" width="' + RW + '" height="' + RH + '" rx="8"/>' +
                '<text class="dp-val" data-el="v-' + r.k + '" x="' + RCX + '" y="' + (r.y + 1) + '">—</text>' +
                '</g>';
        }).join('');
    }

    function cacheBoxes() {
        return ['L1', 'L2', 'L3'].map(function (lv) {
            var g = CGEO[lv], cx = LX[lv], slots = '';
            for (var s = 0; s < CAPS[lv]; s++) {
                slots += '<text class="dp-mini" data-el="ce-' + lv + '-' + s + '" x="' + cx +
                    '" y="' + (g.y + 40 + s * 18) + '" text-anchor="middle">·</text>';
            }
            return '<rect class="dp-blk" data-el="' + lv + '" x="' + g.x + '" y="' + g.y +
                '" width="' + g.w + '" height="' + g.h + '" rx="8"/>' +
                '<text class="dp-blk-label" x="' + cx + '" y="' + (g.y + 20) +
                '" text-anchor="middle" style="font-size:12px">' + lv + '</text>' + slots +
                '<text class="dp-badge" data-el="badge-' + lv + '" x="' + cx +
                '" y="' + (g.y + g.h + 14) + '" opacity="0"></text>';
        }).join('');
    }

    function ramRows() {
        var out = '', i = 0;
        var all = PROGRAM.map(function (p) { return { addr: p.addr, text: itext(p), data: false }; })
            .concat(DATA.map(function (d) { return { addr: d.addr, text: String(d.value), data: true }; }));
        all.forEach(function (row) {
            var y = 96 + i * 50 + (row.data ? 14 : 0);
            out += '<rect class="dp-cell" data-el="cell-' + row.addr + '" x="996" y="' + y +
                '" width="160" height="44" rx="7"/>' +
                '<text class="dp-cell-k" x="1008" y="' + (y + 18) + '">' + hex(row.addr) + '</text>' +
                '<text class="dp-cell-v" data-el="cellv-' + row.addr + '" x="1008" y="' + (y + 34) + '">' +
                row.text + '</text>';
            i++;
        });
        return out;
    }

    var STAGE =
        '<svg class="dp-stage" viewBox="0 0 1200 600" role="img" aria-label="Animated diagram of a CPU, ' +
        'cache hierarchy and RAM. Each step is described in words below the diagram.">' +
        '<g data-el="measure" style="visibility:hidden"></g>' +

        '<rect class="dp-chassis-fill" x="24" y="48" width="536" height="504" rx="16"/>' +
        '<rect class="dp-chassis" data-el="chassis" x="24" y="48" width="536" height="504" rx="16"/>' +
        '<text class="dp-zone" x="44" y="38">Central Processing Unit</text>' +

        /* control spine down the left of the register file */
        '<path class="dp-wire-ctl" data-el="w-ctl" d="M220,148 H240 V468"/>' +
        '<path class="dp-wire-ctl" data-el="w-ctl-pc"  d="M240,132 H272"/>' +
        '<path class="dp-wire-ctl" data-el="w-ctl-ir"  d="M240,216 H272"/>' +
        '<path class="dp-wire-ctl" data-el="w-ctl-mar" d="M240,300 H272"/>' +
        '<path class="dp-wire-ctl" data-el="w-ctl-mdr" d="M240,384 H272"/>' +
        '<path class="dp-wire-ctl" data-el="w-ctl-acc" d="M240,468 H272"/>' +
        '<path class="dp-wire-ctl" data-el="w-ctl-alu" d="M136,200 V300"/>' +
        /* data spine between register file and ALU */
        '<path class="dp-wire" data-el="w-data" d="M256,132 V468"/>' +
        '<path class="dp-wire" d="M256,132 H272"/><path class="dp-wire" d="M256,216 H272"/>' +
        '<path class="dp-wire" d="M256,300 H272"/><path class="dp-wire" d="M256,384 H272"/>' +
        '<path class="dp-wire" d="M256,468 H272"/>' +
        '<path class="dp-wire" data-el="w-alu" d="M206,360 H256"/>' +

        /* three bus rails out to memory */
        '<path class="dp-bus" data-el="rail-addr" d="M536,288 H1000"/>' +
        '<path class="dp-bus" data-el="rail-data" d="M536,300 H1000"/>' +
        '<path class="dp-bus" data-el="rail-ctl"  d="M536,312 H1000"/>' +
        '<text class="dp-blk-sub" x="566" y="342">address · data · control bus</text>' +

        '<rect class="dp-blk" data-el="cu" x="52" y="96" width="168" height="104" rx="10"/>' +
        '<text class="dp-blk-label" data-el="lbl-cu" x="136" y="140" text-anchor="middle">Control Unit</text>' +
        '<text class="dp-blk-sub" x="136" y="160" text-anchor="middle">issues control signals</text>' +
        '<text class="dp-blk-sub" x="136" y="176" text-anchor="middle">holds no data</text>' +

        '<path class="dp-blk" data-el="alu" d="M52,300 L112,300 L136,328 L160,300 L220,300 L192,420 L80,420 Z"/>' +
        '<text class="dp-blk-label" data-el="lbl-alu" x="136" y="368" text-anchor="middle">ALU</text>' +
        '<text class="dp-blk-sub" data-el="alu-op" x="136" y="388" text-anchor="middle">arithmetic + logic</text>' +

        '<rect class="dp-blk" data-el="clock" x="52" y="456" width="168" height="68" rx="10"/>' +
        '<text class="dp-blk-sub" x="68" y="478">Clock</text>' +
        '<path class="dp-wave" d="M68,506 h12 v-16 h16 v16 h16 v-16 h16 v16 h16 v-16 h16 v16 h16 v-16 h16 v16 h12" ' +
        'stroke-dasharray="4 4"/>' +
        '<text class="dp-val" data-el="clock-n" x="196" y="474" text-anchor="end" style="font-size:12px">0</text>' +

        '<text class="dp-zone" x="272" y="80">Registers</text>' + regRows() +

        '<text class="dp-zone" x="596" y="176">Cache</text>' + cacheBoxes() +
        '<text class="dp-blk-sub" x="596" y="428">smallest and fastest</text>' +
        '<text class="dp-blk-sub" x="596" y="444">→ largest and slowest</text>' +

        '<rect class="dp-blk" data-el="ram" x="976" y="48" width="200" height="504" rx="12"/>' +
        '<text class="dp-blk-label" x="996" y="76">RAM</text>' +
        '<text class="dp-blk-sub" x="1156" y="76" text-anchor="end">main memory</text>' + ramRows() +

        '<g data-el="packets"></g></svg>';

    /* ── shared definition ──────────────────────────────────── */

    var def = {
        unit: 'cycle',
        stepLabel: 'Step one cycle',
        stage: STAGE,

        panels: [
            { key: 'log', title: 'Cycle trace' },
            {
                key: 'list', title: 'Program in memory',
                note: '<b>LDA</b> load into ACC · <b>ADD</b> add to ACC · <b>STA</b> store ACC · ' +
                    '<b>HLT</b> stop. Addresses 0x10–0x12 hold the data.'
            },
            {
                key: 'stats', title: 'This run', stats: [
                    { key: 'cycles', label: 'Clock cycles used', note: 'A 3 GHz CPU completes three billion of these every second.' },
                    { key: 'reads', label: 'Memory reads', note: 'Cache hits avoid the trip to RAM entirely.' },
                    { key: 'cache', label: 'Cache hits / misses', initial: '0 / 0', note: 'A hit is served by L1; a miss walks L1 → L2 → L3 → RAM.' }
                ]
            }
        ],

        init: function (ctx) {
            var box = ctx.$('panel-list');
            if (box) {
                box.innerHTML = PROGRAM.map(function (p) {
                    return '<div class="dp-list-row" data-el="pl-' + p.addr + '">' +
                        '<span class="dp-a">' + hex(p.addr) + '</span><span>' + itext(p) + '</span></div>';
                }).join('');
            }
        },

        reset: function (ctx) {
            var s = ctx.state;
            s.mem = {};
            PROGRAM.forEach(function (i) {
                s.mem[i.addr] = { kind: 'instr', text: itext(i), value: null, op: i.op, operand: i.operand };
            });
            DATA.forEach(function (d) {
                s.mem[d.addr] = { kind: 'data', text: String(d.value), value: d.value };
            });
            s.pc = 0; s.ir = null; s.mar = null; s.mdr = null; s.acc = 0;
            s.reads = 0; s.hits = 0; s.misses = 0; s.halted = false; s.instrIndex = -1;
            s.cache = { L1: [], L2: [], L3: [] };

            REGS.forEach(function (r) {
                var t = ctx.$('v-' + r.k); if (t) t.textContent = '—';
                var b = ctx.$('slot-' + r.k); if (b) b.classList.remove('is-changed', 'is-active');
            });
            ctx.$('v-PC').textContent = hex(0);
            ctx.$('v-ACC').textContent = '0';
            ctx.$('clock-n').textContent = '0';
            ctx.$('alu-op').textContent = 'arithmetic + logic';
            DATA.forEach(function (d) {
                var el = ctx.$('cellv-' + d.addr);
                if (el) el.textContent = String(s.mem[d.addr].value);
            });
            ctx.root.querySelectorAll('.dp-list-row').forEach(function (r) { r.classList.remove('is-now'); });
            paintCache(ctx);
            stats(ctx);
            ctx.narrate(
                'The program in RAM adds two numbers and stores the result. Press <b>Step</b> to advance ' +
                'one clock cycle, or <b>Run</b> to watch the whole thing.',
                'Each step is one clock cycle — the same “tick” described in the clock speed paragraph above.');
        },

        /* Keeps the readout tiles in step with the trace — without this the
           cycle count lags behind, because the generator only reaches its
           own bookkeeping when it resumes on the following step. */
        afterStep: function (ctx) { stats(ctx); },

        finish: function (ctx) {
            var s = ctx.state;
            stats(ctx);
            var ns = (ctx.n / 3).toFixed(1);
            var per = Math.round(3e9 / ctx.n / 1e6);
            return 'That whole program — fetch, decode, execute, ' + s.reads + ' memory reads and one write — took <b>' +
                ctx.n + ' clock cycles</b>. A 3 GHz CPU runs three billion cycles every second, so it would finish ' +
                'this in about <b>' + ns + ' nanoseconds</b> and could repeat it roughly <b>' + per +
                ' million times a second</b>. ' + s.hits + ' of the ' + s.reads + ' reads ' +
                (s.hits === 1 ? 'was' : 'were') + ' served by L1 cache instead of RAM — the rest had to travel ' +
                'all the way out to main memory.';
        },

        steps: function (ctx) { return cpu(ctx); }
    };

    /* ── helpers ────────────────────────────────────────────── */

    function paintCache(ctx) {
        ['L1', 'L2', 'L3'].forEach(function (lv) {
            for (var s = 0; s < CAPS[lv]; s++) {
                var el = ctx.$('ce-' + lv + '-' + s);
                if (!el) continue;
                var v = ctx.state.cache[lv][s];
                el.textContent = v !== undefined ? hex(v) : '·';
                el.setAttribute('fill', v !== undefined ? 'var(--text-dark)' : 'var(--text-light)');
            }
        });
    }

    function stats(ctx) {
        var s = ctx.state;
        ctx.stat('cycles', ctx.n, ctx.n
            ? 'At 3 GHz, these ' + ctx.n + ' cycles would take about ' + (ctx.n / 3).toFixed(1) + ' nanoseconds.'
            : 'A 3 GHz CPU completes three billion of these every second.');
        ctx.stat('reads', s.reads);
        ctx.stat('cache', s.hits + ' / ' + s.misses);
    }

    function touch(ctx, lv, addr) {
        var arr = ctx.state.cache[lv], i = arr.indexOf(addr);
        if (i >= 0) arr.splice(i, 1);
        arr.push(addr);
        while (arr.length > CAPS[lv]) arr.shift();
    }

    /* Read through the hierarchy exactly as the text describes:
       L1, then L2, then L3, then RAM. The animation for a miss is
       deliberately much longer than for a hit — the motion is the
       point being taught. */
    function readMemory(ctx, addr) {
        var s = ctx.state;
        s.reads++;
        var inL1 = s.cache.L1.indexOf(addr) >= 0;
        ctx.hot('rail-addr', 'rail-data');
        ctx.activate('slot-MAR');

        return ctx.move('M' + RCX + ',300 H' + LX.L1, hex(addr), ctx.D(280), 'addr').then(function () {
            if (inL1) {
                s.hits++;
                ctx.activate('L1'); ctx.mark('L1', 'is-hit'); ctx.badge('L1', 'HIT', 'hit');
                return ctx.wait(ctx.D(320))
                    .then(function () {
                        return ctx.move('M' + LX.L1 + ',300 H548 V384 H' + RCX,
                            s.mem[addr].text, ctx.D(340), 'data');
                    })
                    .then(function () {
                        s.mdr = s.mem[addr];
                        ctx.setVal('MDR', s.mdr.text);
                        touch(ctx, 'L1', addr);
                        paintCache(ctx); stats(ctx);
                        return { hit: 'L1' };
                    });
            }

            s.misses++;
            var chain = Promise.resolve();
            ['L1', 'L2', 'L3'].forEach(function (lv, i) {
                chain = chain.then(function () {
                    ctx.activate(lv); ctx.mark(lv, 'is-miss'); ctx.badge(lv, 'MISS', 'miss');
                    return ctx.wait(ctx.D(200));
                }).then(function () {
                    if (i === 2) return null;
                    var to = i === 0 ? 'L2' : 'L3';
                    return ctx.move('M' + LX[lv] + ',300 H' + LX[to], hex(addr), ctx.D(240), 'addr');
                });
            });

            return chain
                .then(function () { return ctx.move('M' + LX.L3 + ',300 H' + RAMX, hex(addr), ctx.D(300), 'addr'); })
                .then(function () {
                    ctx.activate('ram', 'cell-' + addr);
                    return ctx.wait(ctx.D(320));
                })
                .then(function () {
                    return ctx.move('M' + RAMX + ',300 H548 V384 H' + RCX, s.mem[addr].text, ctx.D(700), 'data');
                })
                .then(function () {
                    s.mdr = s.mem[addr];
                    ctx.setVal('MDR', s.mdr.text);
                    ['L1', 'L2', 'L3'].forEach(function (lv) { touch(ctx, lv, addr); });
                    paintCache(ctx); stats(ctx);
                    return { hit: null };
                });
        });
    }

    function writeMemory(ctx, addr, value) {
        var s = ctx.state;
        ctx.hot('rail-addr', 'rail-data');
        return ctx.move('M' + RCX + ',384 H548 V300 H' + RAMX, String(value), ctx.D(760), 'data')
            .then(function () {
                s.mem[addr] = { kind: 'data', text: String(value), value: value };
                var el = ctx.$('cellv-' + addr); if (el) el.textContent = String(value);
                ctx.activate('cell-' + addr);
                ['L1', 'L2', 'L3'].forEach(function (lv) { touch(ctx, lv, addr); });
                paintCache(ctx);
            });
    }

    /* ── the fetch–decode–execute cycle ─────────────────────── */

    function* cpu(ctx) {
        var s = ctx.state;
        var MM = ctx.def.markMap || {};

        while (!s.halted) {
            var startPc = s.pc;
            s.instrIndex++;

            /* ── FETCH ── */
            yield {
                phase: 'FETCH', op: 'MAR ← PC', mark: MM['pc-to-mar'],
                plain: 'The control unit copies the address in the Program Counter into the MAR — this is the address of the next instruction.',
                run: function () {
                    ctx.activate('cu', 'lbl-cu');
                    ctx.hot('w-ctl', 'w-ctl-pc', 'w-ctl-mar', 'w-data');
                    if (s.instrIndex >= 1 && MM['sequence']) ctx.earn(MM['sequence'], ctx.n);
                    return ctx.move('M' + RCX + ',132 H' + SPINE + ' V300 H' + RCX, hex(s.pc), ctx.D(560), 'addr')
                        .then(function () { s.mar = s.pc; ctx.setVal('MAR', hex(s.mar)); });
                }
            };

            yield {
                phase: 'FETCH', op: 'MDR ← Memory[MAR]', mark: MM['registers'],
                plain: 'The address goes out on the address bus. The CPU checks each cache level in order before reaching out to RAM.',
                run: function () {
                    return readMemory(ctx, s.mar).then(function (r) {
                        ctx.narrate(
                            'The address goes out on the address bus. <span class="dp-op">MDR ← Memory[' + hex(s.mar) + ']</span>',
                            r.hit
                                ? 'Found in <b>L1 cache</b> — no trip to RAM needed. This is what the text means by “stores copies of frequently accessed data”.'
                                : 'Not in L1, L2 or L3, so the CPU had to reach all the way out to RAM — the slowest path, and you can see how much longer it takes.');
                    });
                }
            };

            yield {
                phase: 'FETCH', op: 'IR ← MDR ; PC ← PC + 1', mark: MM['pc-increment'],
                plain: 'The instruction arrives in the Instruction Register and the Program Counter advances to the next address.',
                run: function () {
                    ctx.activate('cu', 'lbl-cu');
                    ctx.hot('w-data', 'w-ctl-ir');
                    return ctx.move('M' + RCX + ',384 H' + SPINE + ' V216 H' + RCX, s.mdr.text, ctx.D(520), 'data')
                        .then(function () {
                            s.ir = s.mdr; ctx.setVal('IR', s.ir.text);
                            s.pc = s.pc + 1; ctx.setVal('PC', hex(s.pc));
                            ctx.root.querySelectorAll('.dp-list-row').forEach(function (r) { r.classList.remove('is-now'); });
                            var pl = ctx.$('pl-' + s.mar); if (pl) pl.classList.add('is-now');
                        });
                }
            };

            var instr = s.ir;

            /* ── DECODE ── */
            yield {
                phase: 'DECODE', op: 'decode ' + instr.text, mark: MM['decode'],
                plain: 'The control unit decodes the opcode in the IR into control signals.',
                run: function () {
                    ctx.activate('cu', 'lbl-cu');
                    ctx.hot('w-ctl', 'w-ctl-pc', 'w-ctl-ir', 'w-ctl-mar', 'w-ctl-mdr', 'w-ctl-acc', 'w-ctl-alu');
                    ctx.narrate(
                        'The control unit reads <span class="dp-op">' + instr.text + '</span> out of the IR and decodes it into control signals.',
                        'Notice the control unit never touches the data — it only tells the other components what to do next. That is the “conductor of an orchestra” in the study tip above.');
                    return ctx.wait(ctx.D(700));
                }
            };

            /* ── EXECUTE ── */
            if (instr.op === 'HLT') {
                yield {
                    phase: 'EXECUTE', op: 'HLT',
                    plain: 'The halt instruction stops the cycle.',
                    run: function () {
                        ctx.activate('cu', 'lbl-cu');
                        s.halted = true;
                        ctx.narrate('<span class="dp-op">HLT</span> — the control unit stops the clock. The program is finished.',
                            'The result is in memory at <span class="dp-op">0x12</span>, and in the accumulator.');
                        return ctx.wait(ctx.D(400));
                    }
                };
                continue;
            }

            yield {
                phase: 'EXECUTE', op: 'MAR ← ' + hex(instr.operand), mark: MM['registers'],
                plain: 'The control unit puts the operand address into the MAR.',
                run: function () {
                    ctx.activate('cu', 'lbl-cu');
                    ctx.hot('w-ctl', 'w-ctl-mar');
                    return ctx.move('M' + RCX + ',216 H' + SPINE + ' V300 H' + RCX, hex(instr.operand), ctx.D(520), 'addr')
                        .then(function () { s.mar = instr.operand; ctx.setVal('MAR', hex(s.mar)); });
                }
            };

            if (instr.op === 'LDA' || instr.op === 'ADD') {
                yield {
                    phase: 'EXECUTE', op: 'MDR ← Memory[MAR]', mark: MM['registers'],
                    plain: 'The operand is read from memory through the cache hierarchy.',
                    run: function () {
                        return readMemory(ctx, s.mar).then(function (r) {
                            ctx.narrate('Reading the operand at <span class="dp-op">' + hex(s.mar) + '</span> into the MDR.',
                                r.hit
                                    ? '<b>L1 hit</b> — this address was read a moment ago, so it is still in the fastest cache. Compare how long this took against the read before it.'
                                    : '<b>Cache miss</b> at every level, so the value came from RAM.');
                        });
                    }
                };

                if (instr.op === 'LDA') {
                    yield {
                        phase: 'EXECUTE', op: 'ACC ← MDR',
                        plain: 'The value is copied into the accumulator.',
                        run: function () {
                            ctx.hot('w-data', 'w-ctl-acc');
                            return ctx.move('M' + RCX + ',384 H' + SPINE + ' V468 H' + RCX, s.mdr.text, ctx.D(520), 'data')
                                .then(function () {
                                    s.acc = s.mdr.value; ctx.setVal('ACC', s.acc);
                                    ctx.narrate('<span class="dp-op">ACC ← ' + s.acc +
                                        '</span> — the value is now held in the accumulator, ready to be worked on.');
                                });
                        }
                    };
                } else {
                    yield {
                        phase: 'EXECUTE', op: 'ACC ← ACC + MDR', mark: MM['alu'],
                        plain: 'The ALU adds the operand to the accumulator and the result is stored back in the accumulator.',
                        run: function () {
                            var a = s.acc, b = s.mdr.value;
                            ctx.activate('alu', 'lbl-alu', 'cu', 'lbl-cu');
                            ctx.hot('w-ctl-alu', 'w-alu', 'w-data');
                            ctx.$('alu-op').textContent = a + ' + ' + b;
                            ctx.narrate('The ALU receives both operands: <span class="dp-op">' + a +
                                '</span> from the accumulator and <span class="dp-op">' + b + '</span> from the MDR.',
                                'The control unit told it to add — the ALU does the arithmetic, the registers hold the values.');
                            return Promise.all([
                                ctx.move('M' + RCX + ',468 H' + SPINE + ' V360 H' + ALUX, String(a), ctx.D(560), 'data'),
                                ctx.move('M' + RCX + ',384 H' + SPINE + ' V360 H' + ALUX, String(b), ctx.D(560), 'data')
                            ])
                                .then(function () { return ctx.wait(ctx.D(280)); })
                                .then(function () {
                                    s.acc = a + b;
                                    ctx.$('alu-op').textContent = '= ' + s.acc;
                                    return ctx.move('M' + ALUX + ',360 H' + SPINE + ' V468 H' + RCX,
                                        String(s.acc), ctx.D(560), 'data');
                                })
                                .then(function () {
                                    ctx.setVal('ACC', s.acc);
                                    ctx.narrate('<span class="dp-op">' + a + ' + ' + b + ' = ' + s.acc +
                                        '</span> — the result is stored in the accumulator.',
                                        'The markscheme caps this mark if you do not say where the result goes.');
                                    setTimeout(function () {
                                        var el = ctx.$('alu-op');
                                        if (el) el.textContent = 'arithmetic + logic';
                                    }, 1400);
                                });
                        }
                    };
                }
            }

            if (instr.op === 'STA') {
                yield {
                    phase: 'EXECUTE', op: 'MDR ← ACC', mark: MM['registers'],
                    plain: 'The result is copied from the accumulator into the MDR, ready to go out on the data bus.',
                    run: function () {
                        ctx.hot('w-data', 'w-ctl-mdr');
                        return ctx.move('M' + RCX + ',468 H' + SPINE + ' V384 H' + RCX, String(s.acc), ctx.D(520), 'data')
                            .then(function () {
                                s.mdr = { kind: 'data', text: String(s.acc), value: s.acc };
                                ctx.setVal('MDR', s.acc);
                            });
                    }
                };
                yield {
                    phase: 'EXECUTE', op: 'Memory[' + hex(instr.operand) + '] ← MDR',
                    plain: 'The value is written back to memory.',
                    run: function () {
                        ctx.activate('ram');
                        return writeMemory(ctx, instr.operand, s.acc).then(function () {
                            ctx.narrate('<span class="dp-op">' + s.acc + '</span> is written back to memory at <span class="dp-op">' +
                                hex(instr.operand) + '</span>.',
                                'This is the “written back to RAM” step in the paragraph about primary and secondary memory.');
                        });
                    }
                };
            }

            stats(ctx);
            if (startPc === s.pc) s.halted = true;   // safety net
        }
    }

    /* ── register against this topic's own markscheme ───────── */

    DynamicPage.register('A1.1.5', Object.assign({}, def, {
        heading: 'Run the cycle',
        intro: 'The fetch–decode–execute cycle, running one clock cycle at a time. Watch the Program Counter ' +
            'in particular: where its address goes, when it advances, and how that keeps the instructions ' +
            'running in order.',
        markMap: { 'pc-to-mar': 'p1', 'pc-increment': 'p2', 'sequence': 'p3' },
        marks: {
            title: 'This is the answer to Question 1',
            lead: 'Question 1 asks you to explain the role of the Program Counter during the ' +
                'fetch–decode–execute cycle. Each of its three marks lights up as the PC does that job.',
            items: [
                {
                    id: 'p1', t: 'The PC holds the address of the next instruction',
                    d: 'At the start of every fetch its address is copied into the MAR. Do not confuse the PC with the MAR or the IR.'
                },
                {
                    id: 'p2', t: 'The PC is updated after each fetch',
                    d: 'As soon as the instruction reaches the IR, the PC advances to point at the following address.'
                },
                {
                    id: 'p3', t: 'This ensures sequential execution',
                    d: 'Because the PC advanced, the next fetch reads the next instruction in order — 0x00, then 0x01, then 0x02.'
                }
            ]
        }
    }));
})();
