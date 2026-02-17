/**
 * IB Study Companion — ES6 Module Entry Point
 *
 * Imports all modules and attaches public functions to window
 * for backward compatibility with onclick handlers in templates.
 */

// Core utilities
import { escapeHtml, showToast, copyToClipboard, toggleDarkMode, toggleMobileSidebar, COMMAND_TERM_DEFINITIONS } from './modules/utils.js';

// Accessibility
import { openModal, closeModal, announce, toggleDyslexicFont } from './modules/a11y.js';

// API client (side-effect: sets up centralized fetch)
import { api } from './modules/api.js';

// Upload (side-effect: initializes drag-drop listeners)
import { deleteDocument } from './modules/upload.js';

// Study system (side-effect: initializes subject topic sync + speech check)
import {
    selectMode, backToModes, onCommandTermChange, generateStudy,
    selectResponseMode, displayQuestion, submitAnswer, nextQuestion,
    skipQuestion, dismissSessionSummary, toggleSpeechToText,
    uploadAnswerFile, requestHint, showSection, studyState,
} from './modules/study.js';

// Insights & analytics
import { loadInsights, generateWeaknessReport } from './modules/insights.js';

// Lifecycle management
import { toggleMilestone, addCASReflection, updateLifecycleSection } from './modules/lifecycle.js';

// Parent portal
import { toggleParentSharing, copyParentLink, regenerateToken, savePrivacySettings } from './modules/parent.js';

// Study planner
import { generatePlan, togglePlanTask } from './modules/planner.js';

// Notifications (side-effect: loads on DOMContentLoaded)
import { loadNotifications, toggleNotificationPanel, markNotificationRead, markAllNotificationsRead, requestNotificationPermission } from './modules/notifications.js';

// PWA (side-effect: registers install prompt + offline handlers)
import { installApp, dismissInstallBanner } from './modules/pwa.js';

// Question sharing
import { shareQuestion, exportSessionQuestions, importQuestions } from './modules/sharing.js';

// ── Attach all public functions to window for onclick handlers ───

// Utils
window.escapeHtml = escapeHtml;
window.showToast = showToast;
window.copyToClipboard = copyToClipboard;
window.toggleDarkMode = toggleDarkMode;
window.toggleMobileSidebar = toggleMobileSidebar;
window.COMMAND_TERM_DEFINITIONS = COMMAND_TERM_DEFINITIONS;

// Upload
window.deleteDocument = deleteDocument;

// Study
window.selectMode = selectMode;
window.backToModes = backToModes;
window.onCommandTermChange = onCommandTermChange;
window.generateStudy = generateStudy;
window.selectResponseMode = selectResponseMode;
window.displayQuestion = displayQuestion;
window.submitAnswer = submitAnswer;
window.nextQuestion = nextQuestion;
window.skipQuestion = skipQuestion;
window.dismissSessionSummary = dismissSessionSummary;
window.toggleSpeechToText = toggleSpeechToText;
window.uploadAnswerFile = uploadAnswerFile;
window.requestHint = requestHint;

// Insights
window.loadInsights = loadInsights;
window.generateWeaknessReport = generateWeaknessReport;

// Lifecycle
window.toggleMilestone = toggleMilestone;
window.addCASReflection = addCASReflection;
window.updateLifecycleSection = updateLifecycleSection;

// Parent portal
window.toggleParentSharing = toggleParentSharing;
window.copyParentLink = copyParentLink;
window.regenerateToken = regenerateToken;
window.savePrivacySettings = savePrivacySettings;

// Planner
window.generatePlan = generatePlan;
window.togglePlanTask = togglePlanTask;

// Notifications
window.loadNotifications = loadNotifications;
window.toggleNotificationPanel = toggleNotificationPanel;
window.markNotificationRead = markNotificationRead;
window.markAllNotificationsRead = markAllNotificationsRead;
window.requestNotificationPermission = requestNotificationPermission;

// PWA
window.installApp = installApp;
window.dismissInstallBanner = dismissInstallBanner;

// Sharing
window.shareQuestion = shareQuestion;
window.exportSessionQuestions = exportSessionQuestions;
window.importQuestions = importQuestions;

// Accessibility
window.openModal = openModal;
window.closeModal = closeModal;
window.announce = announce;
window.toggleDyslexicFont = toggleDyslexicFont;
