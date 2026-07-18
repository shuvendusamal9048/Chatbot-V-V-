let utterance = null;

export function speak(text) {

  if (!text) return;

  speechSynthesis.cancel();

  utterance =
    new SpeechSynthesisUtterance(
      text
    );

  utterance.lang = "en-IN";

  utterance.rate = 1;

  utterance.pitch = 1;

  speechSynthesis.speak(
    utterance
  );
}

export function stopSpeak() {

  speechSynthesis.cancel();

}