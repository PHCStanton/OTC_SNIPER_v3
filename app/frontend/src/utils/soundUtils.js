/**
 * soundUtils.js — Centralized sound management for UI clicks and trading events.
 */
import { useSettingsStore } from '../stores/useSettingsStore.js';

class SoundManager {
  constructor() {
    this.sounds = {
      CLICK: new Audio('/AUDIO/UIClick-Clean_modern_UI_butt-Elevenlabs.mp3'),
      GHOST_EXECUTE: new Audio('/AUDIO/GHOST_EXECUTE1.ogg'),
      GHOST_WIN: new Audio('/AUDIO/GHOST_WIN2.ogg'),
      GHOST_LOSS: new Audio('/AUDIO/GHOST_LOSS1.ogg'),
      NOTIFICATION: new Audio('/AUDIO/NOTIFICATION_#2.mp3'),
      TIMER_ALERT: new Audio('/AUDIO/iPhone_haptic.mp3'),
    };

    // Preload sounds
    Object.values(this.sounds).forEach((audio) => {
      audio.load();
    });
  }

  playClick() {
    const { uiSoundsEnabled } = useSettingsStore.getState();
    if (uiSoundsEnabled) {
      this._play('CLICK');
    }
  }

  playGhostExecute() {
    const { tradingSoundsEnabled } = useSettingsStore.getState();
    if (tradingSoundsEnabled) {
      this._play('GHOST_EXECUTE');
    }
  }

  playGhostWin() {
    const { tradingSoundsEnabled } = useSettingsStore.getState();
    if (tradingSoundsEnabled) {
      this._play('GHOST_WIN');
    }
  }

  playGhostLoss() {
    const { tradingSoundsEnabled } = useSettingsStore.getState();
    if (tradingSoundsEnabled) {
      this._play('GHOST_LOSS');
    }
  }

  playNotification() {
    const { uiSoundsEnabled } = useSettingsStore.getState();
    if (uiSoundsEnabled) {
      this._play('NOTIFICATION');
    }
  }
  
  playTimerAlert() {
    const { uiSoundsEnabled } = useSettingsStore.getState();
    if (uiSoundsEnabled) {
      this._play('TIMER_ALERT');
    }
  }

  _play(key) {
    const audio = this.sounds[key];
    if (audio) {
      audio.currentTime = 0;
      audio.play().catch((err) => {
        // Chrome and other browsers may block auto-play until user interaction.
        // This is expected and usually resolves after the first click.
        console.warn(`[SoundManager] Could not play ${key}:`, err.message);
      });
    }
  }
}

export const soundManager = new SoundManager();
