import React from 'react';
import { render } from '@testing-library/react-native';
import App from '../src/App';

describe('App', () => {
  it('renders without crashing', () => {
    const { getByText } = render(<App />);
    // Basic smoke test
    expect(getByText).toBeDefined();
  });
});
