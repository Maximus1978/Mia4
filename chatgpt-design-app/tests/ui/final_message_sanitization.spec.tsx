import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import ChatWindow from '../../src/components/Chat/ChatWindow';
import { GenerationSettings } from '../../src/components/Settings/SettingsPopover';
import * as api from '../../src/api';

// Minimal mock props / harness: we assume ChatWindow internally manages state via SSE.
// For a unit snapshot we can simulate final message injection by rendering a simplified
// component path would normally produce. To avoid deep refactor, we rely on an exposed
// helper pattern: create a minimal stub of messages shape expected by ChatWindow if
// it supports props (if not, this test may need adaptation when ChatWindow API changes).

// If ChatWindow does not accept direct injection (common), this test can be adjusted
// after exposing a lightweight prop (future). For now, we assert structural absence
// of service markers in any rendered assistant final bubble text nodes.

describe('Final message sanitization', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('sanitizes leaked service markers from streaming tokens in final bubble', async () => {
    const settings: GenerationSettings = {
      temperature: 0.2,
      top_p: 0.9,
      max_output_tokens: 64,
      persona: '',
      reasoningPreset: 'default',
    } as any;
    // Mock streamGenerate to push tokens containing service markers and then final frame
    const streamSpy = vi.spyOn(api, 'streamGenerate').mockImplementation((
      _params: any,
      cb: api.StreamCallbacks
    ) => {
      // Emit token with leak markers
      cb.onToken?.({ seq: 0, text: '<|start|>assistant|channel|final|message|Hello ', tokens_out: 1, request_id: 'r1', model_id: 'm1' });
      cb.onToken?.({ seq: 1, text: 'World<|end|>', tokens_out: 2, request_id: 'r1', model_id: 'm1' });
      // Final sanitized text the backend would send (already scrubbed)
      cb.onFinal?.({ request_id: 'r1', model_id: 'm1', text: 'Hello World' });
      cb.onUsage?.({
        request_id: 'r1', model_id: 'm1', prompt_tokens: 5, output_tokens: 2,
        latency_ms: 10, decode_tps: 200
      } as any);
      cb.onEnd?.('ok');
      return { cancel: () => undefined, getRequestId: () => 'r1' } as api.StreamHandle;
    });

  const { container } = render(<ChatWindow model={'m1'} settings={settings} />);
    // Simulate user sending a prompt to trigger stream
    const input = container.querySelector('input.input-field') as HTMLInputElement;
  fireEvent.change(input, { target: { value: 'Hi' } });
    const sendBtn = container.querySelector('button.send-button') as HTMLButtonElement;
  fireEvent.click(sendBtn);

    await waitFor(() => {
      const nodes = Array.from(container.querySelectorAll('.ai-wrapper'));
      const aiTexts = nodes.map(n => n.textContent || '').join('\n');
      expect(aiTexts).toContain('Hello World');
    });
    const aiTexts = Array.from(container.querySelectorAll('.ai-wrapper')).map(n => n.textContent || '').join('\n');
    expect(aiTexts).not.toMatch(/<\|start\|>|<\|channel\|>|assistant\|channel\|final/);

    streamSpy.mockRestore();
  });

  it('scrubs fused assistantfinal prefix in UI guard', async () => {
    const settings: GenerationSettings = {
      temperature: 0.1,
      top_p: 0.9,
      max_output_tokens: 32,
      persona: '',
      reasoningPreset: 'default',
    } as any;

    const streamSpy = vi.spyOn(api, 'streamGenerate').mockImplementation((
      _params: any,
      cb: api.StreamCallbacks
    ) => {
      cb.onToken?.({
        seq: 0,
        text: 'assistantfinal',
        tokens_out: 1,
        request_id: 'r2',
        model_id: 'm1'
      });
      cb.onToken?.({
        seq: 1,
        text: ' Hello again',
        tokens_out: 2,
        request_id: 'r2',
        model_id: 'm1'
      });
      cb.onFinal?.({
        request_id: 'r2',
        model_id: 'm1',
        text: 'assistantfinal Hello again'
      });
      cb.onUsage?.({
        request_id: 'r2',
        model_id: 'm1',
        prompt_tokens: 4,
        output_tokens: 2,
        latency_ms: 12,
        decode_tps: 150
      } as any);
      cb.onEnd?.('ok');
      return { cancel: () => undefined, getRequestId: () => 'r2' } as api.StreamHandle;
    });

  const { container } = render(<ChatWindow model={'m1'} settings={settings} />);
    const input = container.querySelector('input.input-field') as HTMLInputElement;
  fireEvent.change(input, { target: { value: 'Hi again' } });
    const sendBtn = container.querySelector('button.send-button') as HTMLButtonElement;
  fireEvent.click(sendBtn);

    await waitFor(() => {
      const node = container.querySelector('.ai-message-text') as HTMLElement | null;
      expect(node).toBeTruthy();
      expect(node?.textContent).toContain('Hello again');
    });
    const aiNode = container.querySelector('.ai-message-text') as HTMLElement;
    expect(aiNode.textContent?.toLowerCase().startsWith('assistantfinal')).toBe(false);
    expect(aiNode.textContent).toContain('Hello again');
    expect(aiNode.dataset.scrubbed).toBe('true');
    expect(aiNode.dataset.original).toContain('assistantfinal');

    streamSpy.mockRestore();
  });
});
