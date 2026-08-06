import { stripLegacyMarkers } from '../../lib/messageMarkers';

describe('stripLegacyMarkers', () => {
  it('leaves plain text untouched', () => {
    expect(stripLegacyMarkers('Here is my analysis of AAPL.')).toBe('Here is my analysis of AAPL.');
  });

  it('removes a {{visualization:...}} marker', () => {
    expect(stripLegacyMarkers('See the chart below.\n{{visualization:revenue.html}}')).toBe(
      'See the chart below.\n'
    );
  });

  it('removes the legacy [visualization: ...] form', () => {
    expect(stripLegacyMarkers('before [visualization:  margins.html ] after')).toBe('before  after');
  });

  it('removes multiple markers', () => {
    expect(stripLegacyMarkers('Intro {{visualization:a.html}} mid {{visualization:b.html}} end')).toBe(
      'Intro  mid  end'
    );
  });

  it('collapses the excess blank lines a stripped marker leaves behind', () => {
    expect(stripLegacyMarkers('text\n\n\n{{visualization:a.html}}')).toBe('text\n\n');
  });

  it('returns an empty string for empty input', () => {
    expect(stripLegacyMarkers('')).toBe('');
  });
});
