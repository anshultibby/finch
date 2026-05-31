import { parseMessageParts, hasVisualization } from '../../lib/messageMarkers';

describe('parseMessageParts', () => {
  it('returns a single text part when there are no markers', () => {
    const parts = parseMessageParts('Here is my analysis of AAPL.');
    expect(parts).toEqual([{ type: 'text', value: 'Here is my analysis of AAPL.' }]);
  });

  it('extracts a {{visualization:...}} marker into a chip part', () => {
    const parts = parseMessageParts('See the chart below.\n{{visualization:revenue.html}}');
    expect(parts).toEqual([
      { type: 'text', value: 'See the chart below.\n' },
      { type: 'visualization', filename: 'revenue.html' },
    ]);
  });

  it('supports the legacy [visualization: ...] form and trims whitespace', () => {
    const parts = parseMessageParts('[visualization:  margins.html ]');
    expect(parts).toEqual([{ type: 'visualization', filename: 'margins.html' }]);
  });

  it('handles text before, between, and after multiple markers', () => {
    const parts = parseMessageParts(
      'Intro {{visualization:a.html}} middle {{visualization:b.html}} end'
    );
    expect(parts).toEqual([
      { type: 'text', value: 'Intro ' },
      { type: 'visualization', filename: 'a.html' },
      { type: 'text', value: ' middle ' },
      { type: 'visualization', filename: 'b.html' },
      { type: 'text', value: ' end' },
    ]);
  });

  it('drops whitespace-only text fragments around markers', () => {
    const parts = parseMessageParts('{{visualization:a.html}}\n\n');
    expect(parts).toEqual([{ type: 'visualization', filename: 'a.html' }]);
  });

  it('ignores an empty filename marker', () => {
    const parts = parseMessageParts('{{visualization:}}');
    expect(parts).toEqual([]);
  });

  it('returns an empty array for empty input', () => {
    expect(parseMessageParts('')).toEqual([]);
  });
});

describe('hasVisualization', () => {
  it('detects both marker forms', () => {
    expect(hasVisualization('text {{visualization:x.html}}')).toBe(true);
    expect(hasVisualization('[visualization: y.html]')).toBe(true);
  });

  it('is false for plain text and empty input', () => {
    expect(hasVisualization('no charts here')).toBe(false);
    expect(hasVisualization('')).toBe(false);
  });
});
