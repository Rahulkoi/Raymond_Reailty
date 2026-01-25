class PCMWorklet extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      const pcm = new Float32Array(input[0]);
      this.port.postMessage(pcm);
    }
    return true;
  }
}

registerProcessor("pcm-worklet", PCMWorklet);
