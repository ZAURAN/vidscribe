import sys, time, json
import numpy as np
import mlx.core as mx
from mlx_audio.stt.generate import main
AUTO = "--language" not in sys.argv  # no -l: detect the language of every piece (mlx-audio would force "en")
try:
    from mlx_audio.stt.models.qwen3_asr.qwen3_asr import Qwen3ASRModel as M
    piece = M._generate_single_chunk
    seen = [0]  # samples in earlier pieces, for warning times
    def run(self, audio, start, max_tokens, kw):
        sr = self.sample_rate
        cap = min(max_tokens, 32 + int(25 * len(audio) / sr))
        if cap <= 0:
            return "", 0, 0
        text, p, g = piece(self, audio, max_tokens=cap, **kw)
        if g < cap:
            return text, p, g
        if len(audio) < 8 * sr:
            span = "-".join(time.strftime("%H:%M:%S", time.gmtime(t / sr)) for t in (start, start + len(audio)))
            print(f"warning: transcript cut off in {span} (likely a repetition loop)", file=sys.stderr)
            return text, p, g
        lo, hi, w = len(audio) // 4, 3 * len(audio) // 4, sr // 10  # quietest 100 ms in the middle half
        cut = lo + int(np.argmin(np.convolve(np.square(audio[lo:hi], dtype=np.float32), np.ones(w), "valid"))) + w // 2
        t1, p1, g1 = run(self, audio[:cut], start, max_tokens, kw)
        t2, p2, g2 = run(self, audio[cut:], start + cut, max_tokens - g1, kw)
        t2 = self.extract_language(t2)[1] if t2.startswith("language ") else t2  # one language tag per piece
        return " ".join(t for t in (t1.strip(), t2.strip()) if t), p1 + p2, g1 + g2
    # Qwen3-ASR's prompt wants full names: "language zh" is an unknown tag
    NAMES = dict(zh="Chinese", en="English", yue="Cantonese", ar="Arabic", de="German", fr="French", es="Spanish",
                 pt="Portuguese", id="Indonesian", it="Italian", ko="Korean", ru="Russian", th="Thai", vi="Vietnamese",
                 ja="Japanese", tr="Turkish", hi="Hindi", ms="Malay", nl="Dutch", sv="Swedish", da="Danish", fi="Finnish",
                 pl="Polish", cs="Czech", fil="Filipino", tl="Filipino", fa="Persian", el="Greek", ro="Romanian",
                 hu="Hungarian", mk="Macedonian")
    def capped(self, audio, *, max_tokens, language=None, **kw):
        start = seen[0]; seen[0] += len(audio)
        # mlx-audio locks later pieces to the first one's language, so music after English speech
        # looped as "oh, oh, ..."; detect per piece instead (upstream strips only the first piece's tag)
        lang = None if AUTO else NAMES.get(language.lower(), language)
        text, p, g = run(self, audio, start, max_tokens, dict(kw, language=lang))
        if AUTO and language is not None and text.startswith("language "):
            text = self.extract_language(text)[1]
        return text, p, g
    M._generate_single_chunk = capped
    from mlx_audio.lm.models.cache import KVCache
    # mlx-audio's batched loop has no per-piece cap, so one looping piece would stall its batch until the
    # file budget ran out, and 0.5.x keeps later pieces' language tags. Here each piece gets the cap above;
    # one that hits it is redone alone and unpadded by run(), since silence padding can cause the loop.
    def batched(self, chunks, *, max_tokens, sampler, logits_processors, language, system_prompt, batch_size, verbose):
        sr, eos = self.sample_rate, self._eos_token_ids()
        lang = None if AUTO else NAMES.get(language.lower(), language)
        texts, gens, prompts = [], [], []
        for b0 in range(0, len(chunks), batch_size):
            group = chunks[b0:b0 + batch_size]
            pad_to = max(len(a) for a, _ in group)
            caps = [32 + int(25 * len(a) / sr) for a, _ in group]
            embeds = []
            for a, _ in group:
                feats, fmask, n = self._preprocess_audio(np.pad(a, (0, pad_to - len(a))))
                ids = self._build_prompt(n, lang, system_prompt)
                embeds.append(self._build_inputs_embeds(ids, self.get_audio_features(feats, fmask))[0])
            x = mx.stack(embeds)
            cache = [KVCache() for _ in range(self.config.text_config.num_hidden_layers)]
            hidden = self.model(inputs_embeds=x, cache=cache)[:, -1:, :]
            head = self.lm_head if self.lm_head is not None else self.model.embed_tokens.as_linear
            y = sampler(head(hidden)[:, -1, :]); mx.async_eval(y)
            out, done = [[] for _ in group], [False] * len(group)
            while not all(done):
                nxt = sampler(self._forward_with_embeds(self.model.embed_tokens(y[:, None]), cache)[:, -1, :])
                mx.async_eval(nxt)  # the GPU runs the next step while Python reads this one
                for i, t in enumerate(y.tolist()):
                    if done[i]:
                        continue
                    if t in eos:
                        done[i] = True
                    else:
                        out[i].append(t); done[i] = len(out[i]) >= caps[i]
                y = nxt
            width = x.shape[1]
            del x, embeds, cache, hidden  # free the batch before any retry
            for i, (a, off) in enumerate(group):
                text, p, g = self._tokenizer.decode(out[i], skip_special_tokens=True), width, len(out[i])
                if g >= caps[i]:
                    text, p, g = run(self, a, int(off * sr), max_tokens, dict(
                        sampler=sampler, logits_processors=logits_processors, language=lang, system_prompt=system_prompt))
                if AUTO and b0 + i and text.startswith("language "):
                    text = self.extract_language(text)[1]  # upstream reads the first piece's tag
                texts.append(text); gens.append(g); prompts.append(p)
            mx.clear_cache()
        return texts, gens, prompts, [True] * len(chunks)
    M._generate_chunks_batched = batched
except (ImportError, AttributeError) as e:
    print(f"warning: mlx-audio changed, per-piece token cap off ({e})", file=sys.stderr)
# mlx-audio drops --context (not a Qwen3-ASR generate() argument); the model's hotword field is system_prompt
gen = {"language": None} if AUTO else {}
if "--context" in sys.argv:
    i = sys.argv.index("--context")
    gen["system_prompt"] = sys.argv[i + 1]; del sys.argv[i:i + 2]
if gen:
    sys.argv += ["--gen-kwargs", json.dumps(gen)]
sys.argv[0] = "mlx_audio.stt.generate"
main()
