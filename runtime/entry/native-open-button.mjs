// The host provides GenUI.issueNewTurn; we pass the original signed full-text relay.
const RELAY_HEADER = /^WARDROBE2_RELAY [A-Za-z0-9][A-Za-z0-9_-]{0,95} [A-Za-z0-9_-]{1,96} [0-9a-f]{64}$/;

export function nativeOpenButtonProps(chatUi, issueNewTurn) {
  const ui = chatUi?.native_ui;
  if (ui?.show_open_button !== true || typeof ui.open_button_message !== "string" ||
      typeof issueNewTurn !== "function") {
    return null;
  }
  const message = ui.open_button_message;
  const separator = message.indexOf("\n\n");
  if (separator < 0 || !RELAY_HEADER.test(message.slice(0, separator)) ||
      !message.slice(separator + 2).trim()) {
    return null;
  }
  return {
    children: "打开衣橱",
    onClick: () => issueNewTurn(message),
  };
}

// Render both mode lines as always-visible footer text.
export function nativeOpenCardProps(chatUi, issueNewTurn) {
  const openButton = nativeOpenButtonProps(chatUi, issueNewTurn);
  if (!openButton) return null;
  return {openButton, modeStatus: chatUi.mode_card?.status, modeCommands: chatUi.mode_card?.commands};
}
