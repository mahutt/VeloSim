/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

export interface TranslationTable {
  [key: string]: string | TranslationTable;
}

export const EN_TRANSLATIONS = {
  nav: {
    section: {
      main: 'Main',
      admin: 'Admin',
    },
    simulations: 'Simulations',
    scenarios: 'Scenarios',
    users: 'Users',
  },
  user: {
    role: {
      admin: 'Admin',
      user: 'User',
    },
    menu: {
      preferences: 'Preferences',
      changePassword: 'Change password',
      logout: 'Log out',
    },
  },
  common: {
    cancel: 'Cancel',
    close: 'Close',
    retry: 'Retry',
    save: 'Save',
    update: 'Update',
    loading: 'Loading...',
  },
  preferences: {
    title: 'Preferences',
    description: 'Update your personal preferences.',
    language: {
      label: 'Language',
      help: 'Select the language used by the interface.',
      english: 'English',
      french: 'French',
    },
    saveError: 'Could not save preferences. Please try again.',
  },
  resetPassword: {
    title: {
      self: 'Update your password',
      other: 'Update password for',
    },
    description:
      "Enter the same (new) password twice. Click update when you're done.",
    password: 'Password',
    newPasswordPlaceholder: 'New password',
    confirmPassword: 'Confirm password',
    confirmPasswordPlaceholder: 'Confirm new password',
    validation: {
      passwordMin: 'Password must be at least 1 character.',
      passwordsDontMatch: "Passwords don't match",
    },
    success: 'Password updated successfully',
    error: 'Something went wrong',
  },
  login: {
    username: 'Username',
    usernamePlaceholder: 'Username',
    password: 'Password',
    passwordPlaceholder: 'Password',
    submit: 'Log in',
    error: {
      invalidCredentials: 'Invalid credentials',
      serverError: 'Server error, please try again later',
      unknown: 'An unknown error occurred',
    },
    validation: {
      usernameMin: 'Username must be at least 1 character.',
      usernameMax: 'Username must be at most 100 characters.',
      passwordMin: 'Password must be at least 1 character.',
    },
  },
  users: {
    title: 'Users',
    column: {
      id: 'ID',
      username: 'Username',
      type: 'Type',
      status: 'Status',
    },
    status: {
      enabled: 'Enabled',
      disabled: 'Disabled',
    },
    actions: {
      openMenu: 'Open menu',
      makeAdmin: 'Make admin',
      revokeAdmin: 'Revoke admin',
      enableUser: 'Enable user',
      disableUser: 'Disable user',
    },
    filterPlaceholder: 'Filter usernames...',
    newUser: 'New user',
    dialog: {
      createTitle: 'Create new user',
      createDescription: 'Create a new user by filling out the form below.',
      usernameLabel: 'Username',
      usernamePlaceholder: 'Username',
      passwordLabel: 'Password',
      passwordPlaceholder: 'Password',
      adminLabel: 'Admin',
      enabledLabel: 'Enabled',
      close: 'Close',
      create: 'Create',
      success: 'User created successfully',
      genericError: 'Something went wrong',
    },
    validation: {
      usernameMin: 'Username must be at least 1 character.',
      usernameMax: 'Username must be at most 100 characters.',
      passwordMin: 'Password must be at least 1 character.',
    },
    noResults: 'No results.',
    previous: 'Previous',
    next: 'Next',
  },
  simulations: {
    title: 'Simulations',
    column: {
      id: 'ID',
      name: 'Name',
      created: 'Created',
      completion: 'Completion',
      reportSummary: 'Report summary',
      playback: 'Playback',
      report: 'Report',
      updated: 'Updated',
      action: 'Action',
    },
    action: {
      resume: 'Resume',
      download: 'Download',
      preview: 'Preview',
      report: 'Report',
    },
    report: {
      overview: 'Report Overview',
      loading: 'Loading report...',
      legend: {
        title: 'Report summary legend',
        servicingToDrivingRatio: 'Servicing to Driving Ratio',
        vehicleUtilizationRatio: 'Vehicle Utilization Ratio',
        averageTasksServicedPerShift: 'Average Tasks Serviced Per Shift',
        averageTaskResponseTime: 'Average Task Response Time',
        totalVehicleDistanceTravelled: 'Total Vehicle Distance Travelled',
      },
    },
    noResults: 'No results.',
    previous: 'Previous',
    next: 'Next',
    error: {
      loadTitle: 'Failure loading simulations',
      loadPartial: 'Some simulations may be missing from the list.',
      loadAll: 'All simulations failed to load.',
      downloadReport: 'Error downloading simulation report',
      previewReport: 'Error loading simulation report preview',
    },
  },
  map: {
    error: {
      loadTitle: 'Failed to load map',
      loadDescription:
        'An error occurred while loading the map. Please try again later.',
    },
    labels: {
      day: 'Day',
      showAllRoutes: 'Show All Routes',
      tasksCount: 'Tasks ({{count}})',
      tasksSelectedCount: 'Tasks ({{selected}}/{{total}} selected)',
      taskSingular: 'task',
      taskPlural: 'tasks',
      stationsCount: '{{count}} Stations ({{tasks}} tasks)',
      driverId: 'Driver #{{id}}',
      stationId: 'Station #{{id}}',
      stationFallback: 'Station #{{id}}',
      noTasks: 'No tasks',
      taskId: 'Task #{{id}}',
      servicing: 'Servicing',
    },
    assignment: {
      assign: 'Assign',
      reassign: 'Re-assign',
      unassign: 'Un-assign',
      confirm: 'Confirm',
      confirming: 'Confirming...',
      assigning: 'Assigning...',
      remaining: 'Remaining ({{count}})',
      all: 'All ({{count}})',
      batterySingular: 'battery',
      batteryPlural: 'batteries',
      driverHasBatteries: '{{driver}} has {{count}} {{batteryWord}} remaining.',
      assignTasksAnyway: '{{action}} {{count}} {{taskWord}} anyway?',
      alreadyAssigned:
        '({{count}} {{taskWord}} already assigned to other drivers)',
      unassignSingle: 'Un-assign task #{{taskId}} from {{driver}}?',
      reassignMultiFromTo: 'Re-assign {{count}} tasks from {{from}} to {{to}}?',
      reassignSingleFromTo:
        'Re-assign task #{{taskId}} from {{from}} to {{to}}?',
      reassignMultiTo: 'Re-assign {{count}} tasks to {{to}}?',
      assignMultiTo: 'Assign {{count}} tasks to {{to}}?',
      assignSingleTo: 'Assign task #{{taskId}} to {{to}}?',
    },
  },
  taskAssignmentBanner: {
    unassign: {
      single: {
        withStation:
          'Un-assign task #{{taskId}} at {{stationName}} from {{driverName}}?',
        withoutStation: 'Un-assign task #{{taskId}} from {{driverName}}?',
      },
      multi: {
        withStation:
          'Un-assign {{count}} tasks at {{stationName}} from {{driverName}}?',
        withoutStation: 'Un-assign {{count}} tasks from {{driverName}}?',
      },
    },
  },
  driverStateBadge: {
    offShift: {
      label: 'Off shift',
      short: 'Off',
    },
    pendingShift: {
      label: 'Pending shift',
      short: 'Pending',
    },
    idle: {
      label: 'Idle',
      short: 'Idle',
    },
    onRoute: {
      label: 'On route',
      short: 'On route',
    },
    servicing: {
      label: 'Servicing',
      short: 'Servicing',
    },
    onBreak: {
      label: 'On break',
      short: 'Break',
    },
    endingShift: {
      label: 'Ending shift',
      short: 'Ending',
    },
    seekingHQForInventory: {
      label: 'Returning for restock',
      short: 'Return',
    },
    restockingBatteries: {
      label: 'Restocking',
      short: 'Restock',
    },
  },
  simulation: {
    hqWidget: {
      allQuiet: 'All quiet at HQ',
      driverSingular: 'driver',
      driverPlural: 'drivers',
      vehicleSingular: 'vehicle',
      vehiclePlural: 'vehicles',
      atHQ: 'at HQ',
      noPendingShifts: 'No pending shifts',
    },
  },
  diversity: {
    backToHome: 'Back to Home',
    pageTitle: 'Diversity Statement',
    englishTab: 'English',
    frenchTab: 'Français',
    commitmentTitleEn: 'Our Commitment',
    commitmentTitleFr: 'Notre Engagement',
  },
  scenario: {
    editorTitle: 'Scenario Editor',
    dropToImport: 'Drop to import scenario',
    name: 'Scenario name',
    description: 'Description',
    descriptionPlaceholder: 'Enter scenario description',
    jsonLabel: 'Scenario JSON',
    jsonPlaceholder: 'Paste or type your JSON scenario here...',
    import: 'Import',
    new: 'New',
    edit: 'Edit',
    export: 'Export',
    startSimulation: 'Start Simulation',
    savedScenarios: 'Saved Scenarios',
    noSavedScenarios: 'No saved scenarios',
    deleteAriaPrefix: 'Delete',
    option: {
      addStation: 'Add Station',
      addVehicle: 'Add Vehicle',
      addDriver: 'Add Driver',
      useGbfsStations: 'Use GBFS Stations',
    },
    toast: {
      station: 'Station',
      driver: 'Driver',
      vehicle: 'Vehicle',
      addedSuccessfully: 'added successfully',
      gbfsFetchFailed: 'Failed to fetch GBFS station information',
      gbfsLoaded: 'GBFS stations loaded successfully',
    },
    dialog: {
      simulationNameTitle: 'Name your simulation',
      simulationNameDescription:
        'Give this simulation a name to help you identify it later.',
      simulationNameLabel: 'Simulation name',
      simulationNamePlaceholder: 'Enter simulation name',
      start: 'Start',
      scenarioNameRequiredTitle: 'Scenario Name Required',
      scenarioNameRequiredDescription:
        'Please enter a name for your scenario to continue.',
      scenarioNameLabel: 'Scenario Name',
      scenarioNamePlaceholder: 'Enter scenario name',
      continue: 'Continue',
      overwriteTitle: 'Overwrite or Save As New?',
      overwriteDescriptionPrefix: 'You are editing the scenario',
      overwriteDescriptionSuffix:
        'Would you like to overwrite the existing scenario or save as a new one?',
      saveAsNew: 'Save As New',
      overwrite: 'Overwrite',
      unsavedChangesTitle: 'Unsaved Changes',
      unsavedChangesDescription:
        'You have unsaved changes. Are you sure you want to leave? Your changes will be lost.',
      discard: 'Discard',
      deleteTitle: 'Delete Scenario',
      deleteDescriptionPrefix: 'Are you sure you want to delete',
      deleteDescriptionSuffix: 'This action cannot be undone.',
      delete: 'Delete',
      addStationTitle: 'Add Station',
      addStationDescription:
        'Configure a new station to insert into the scenario.',
      stationNameLabel: 'Station Name',
      stationNamePlaceholder: 'e.g., Main Street Station',
      latitudeLabel: 'Latitude',
      latitudePlaceholder: 'e.g., 45.5017',
      longitudeLabel: 'Longitude',
      longitudePlaceholder: 'e.g., -73.5673',
      scheduledTasksOptionalLabel: 'Scheduled Tasks (optional)',
      scheduledTasksPlaceholder: 'e.g., day1:09:30, day1:14:00, day2:10:15',
      initialTaskCountOptionalLabel: 'Initial Task Count (optional)',
      initialTaskCountPlaceholder: 'e.g., 5',
      addStationAction: 'Add Station',
      addDriverTitle: 'Add Driver',
      addDriverDescription:
        'Configure a new driver to insert into the scenario.',
      driverNameLabel: 'Driver Name',
      driverNamePlaceholder: 'e.g., Driver 1',
      shiftStartTimeLabel: 'Shift Start Time',
      shiftStartTimePlaceholder: 'e.g., day1:08:00',
      shiftEndTimeLabel: 'Shift End Time',
      shiftEndTimePlaceholder: 'e.g., day1:17:00',
      lunchBreakOptionalLabel: 'Lunch Break (optional)',
      lunchBreakPlaceholder: 'e.g., day1:12:00',
      addDriverAction: 'Add Driver',
      addVehicleTitle: 'Add Vehicle',
      addVehicleDescription:
        'Configure a new vehicle to insert into the scenario.',
      vehicleNameLabel: 'Vehicle Name',
      vehicleNamePlaceholder: 'e.g., Vehicle 1',
      latitudeOptionalLabel: 'Latitude (optional)',
      longitudeOptionalLabel: 'Longitude (optional)',
      batteryCountOptionalLabel: 'Battery Count (optional)',
      batteryCountPlaceholder: 'e.g., 5',
      batteryCountHint:
        'Leave empty to start at HQ with 0 batteries. If position is provided, vehicle starts at that location.',
      addVehicleAction: 'Add Vehicle',
    },
    validation: {
      driver: {
        nameRequired: 'Driver name is required',
        startTimeRequired: 'Start time is required',
        startTimeFormat: 'Invalid format. Use dayN:HH:MM (e.g., day1:08:00)',
        endTimeRequired: 'End time is required',
        endTimeFormat: 'Invalid format. Use dayN:HH:MM (e.g., day1:17:00)',
        endAfterStart: 'End time must be after start time',
        lunchFormat: 'Invalid format. Use dayN:HH:MM (e.g., day1:12:00)',
        lunchBetween: 'Lunch break must be between start and end time',
      },
      station: {
        nameRequired: 'Station name is required',
        latitudeRequired: 'Valid latitude is required',
        latitudeRange: 'must be between {{min}} and {{max}}',
        longitudeRequired: 'Valid longitude is required',
        longitudeRange: 'must be between {{min}} and {{max}}',
        initialTaskNonNegative: 'Must be a non-negative number',
        scheduledTaskFormat:
          'Invalid format: "{{task}}". Must be dayN:HH:MM (e.g., day1:09:30)',
      },
      vehicle: {
        nameRequired: 'Vehicle name is required',
        insufficientDrivers: 'Insufficient drivers for positioned vehicle',
        latitudeRequiredWhenLongitude:
          'Latitude is required when longitude is provided',
        latitudeRequired: 'Valid latitude is required',
        latitudeRange: 'must be between {{min}} and {{max}}',
        longitudeRequiredWhenLatitude:
          'Longitude is required when latitude is provided',
        longitudeRequired: 'Valid longitude is required',
        longitudeRange: 'must be between {{min}} and {{max}}',
        batteryNonNegative: 'Must be a non-negative number',
      },
    },
    error: {
      loadScenariosTitle: 'Failure loading scenarios',
      loadScenariosPartial: 'Some scenarios may be missing from the list.',
      loadScenariosAll: 'All scenarios failed to load.',
      importTitle: 'Import Failed',
      importDescription: 'The file is not a valid JSON scenario.',
      noScenarioTitle: 'No Scenario',
      noScenarioDescription:
        'Please create or load a scenario before starting simulation.',
      invalidTitle: 'Invalid Scenario',
      invalidDescription: 'Invalid JSON format',
      noContentToProcessTitle: 'No content to process',
      noContentToProcessDescription: 'Please enter or load a scenario first.',
      invalidJsonTitle: 'Invalid JSON format',
      invalidJsonDescription:
        'The scenario content is not valid JSON. Please fix the formatting.',
      validationFailedTitle: 'Scenario validation failed',
      validationTitle: 'Validation error',
      downloadFailedTitle: 'Download failed',
      downloadFailedDescription:
        'An unexpected error occurred while downloading the file. Please try again.',
      noContentToSaveTitle: 'No content to save',
      noContentToSaveDescription: 'Please enter a scenario first.',
      saveFailedTitle: 'Failed to save scenario',
      overwriteFailedTitle: 'Failed to overwrite scenario',
      deleteFailedTitle: 'Failed to delete scenario',
      initializeTitle: 'Initialization Failed',
      unableToLoadTitle: 'Unable to load scenario',
      unableToLoadDescription: 'The scenario could not be parsed as JSON.',
    },
  },
} as const satisfies TranslationTable;

type DeepStringSchema<T> = {
  [K in keyof T]: T[K] extends string ? string : DeepStringSchema<T[K]>;
};

export type TranslationSchema = DeepStringSchema<typeof EN_TRANSLATIONS>;

export function formatTranslation(
  template: string,
  values: Record<string, string | number>
): string {
  return Object.entries(values).reduce((result, [key, value]) => {
    return result.replaceAll(`{{${key}}}`, String(value));
  }, template);
}

export const FR_TRANSLATIONS = {
  nav: {
    section: {
      main: 'Principal',
      admin: 'Admin',
    },
    simulations: 'Simulations',
    scenarios: 'Scénarios',
    users: 'Utilisateurs',
  },
  user: {
    role: {
      admin: 'Admin',
      user: 'Utilisateur',
    },
    menu: {
      preferences: 'Préférences',
      changePassword: 'Changer le mot de passe',
      logout: 'Se déconnecter',
    },
  },
  common: {
    cancel: 'Annuler',
    close: 'Fermer',
    retry: 'Réessayer',
    save: 'Enregistrer',
    update: 'Mettre à jour',
    loading: 'Chargement...',
  },
  preferences: {
    title: 'Préférences',
    description: 'Mettez à jour vos préférences personnelles.',
    language: {
      label: 'Langue',
      help: "Sélectionnez la langue utilisée par l'interface.",
      english: 'Anglais',
      french: 'Français',
    },
    saveError: "Impossible d'enregistrer les préférences. Réessayez.",
  },
  resetPassword: {
    title: {
      self: 'Mettre à jour votre mot de passe',
      other: 'Mettre à jour le mot de passe de',
    },
    description:
      'Entrez le même nouveau mot de passe deux fois. Cliquez sur Mettre à jour.',
    password: 'Mot de passe',
    newPasswordPlaceholder: 'Nouveau mot de passe',
    confirmPassword: 'Confirmer le mot de passe',
    confirmPasswordPlaceholder: 'Confirmer le nouveau mot de passe',
    validation: {
      passwordMin: 'Le mot de passe doit contenir au moins 1 caractère.',
      passwordsDontMatch: 'Les mots de passe ne correspondent pas.',
    },
    success: 'Mot de passe mis à jour',
    error: "Une erreur s'est produite",
  },
  login: {
    username: "Nom d'utilisateur",
    usernamePlaceholder: "Nom d'utilisateur",
    password: 'Mot de passe',
    passwordPlaceholder: 'Mot de passe',
    submit: 'Se connecter',
    error: {
      invalidCredentials: 'Identifiants invalides',
      serverError: 'Erreur serveur, veuillez réessayer plus tard',
      unknown: 'Une erreur inconnue est survenue',
    },
    validation: {
      usernameMin: "Le nom d'utilisateur doit contenir au moins 1 caractère.",
      usernameMax: "Le nom d'utilisateur doit contenir au plus 100 caractères.",
      passwordMin: 'Le mot de passe doit contenir au moins 1 caractère.',
    },
  },
  users: {
    title: 'Utilisateurs',
    column: {
      id: 'ID',
      username: "Nom d'utilisateur",
      type: 'Type',
      status: 'Statut',
    },
    status: {
      enabled: 'Activé',
      disabled: 'Désactivé',
    },
    actions: {
      openMenu: 'Ouvrir le menu',
      makeAdmin: 'Nommer admin',
      revokeAdmin: 'Retirer admin',
      enableUser: 'Activer utilisateur',
      disableUser: 'Désactiver utilisateur',
    },
    filterPlaceholder: "Filtrer les noms d'utilisateur...",
    newUser: 'Nouvel utilisateur',
    dialog: {
      createTitle: 'Créer un nouvel utilisateur',
      createDescription:
        'Créez un nouvel utilisateur en remplissant le formulaire ci-dessous.',
      usernameLabel: "Nom d'utilisateur",
      usernamePlaceholder: "Nom d'utilisateur",
      passwordLabel: 'Mot de passe',
      passwordPlaceholder: 'Mot de passe',
      adminLabel: 'Admin',
      enabledLabel: 'Activé',
      close: 'Fermer',
      create: 'Créer',
      success: 'Utilisateur créé avec succès',
      genericError: "Une erreur s'est produite",
    },
    validation: {
      usernameMin: "Le nom d'utilisateur doit contenir au moins 1 caractère.",
      usernameMax: "Le nom d'utilisateur doit contenir au plus 100 caractères.",
      passwordMin: 'Le mot de passe doit contenir au moins 1 caractère.',
    },
    noResults: 'Aucun résultat.',
    previous: 'Précédent',
    next: 'Suivant',
  },
  simulations: {
    title: 'Simulations',
    column: {
      id: 'ID',
      name: 'Nom',
      created: 'Créée',
      completion: 'Progression',
      reportSummary: 'Résumé du rapport',
      playback: 'Lecture',
      report: 'Rapport',
      updated: 'Mise à jour',
      action: 'Action',
    },
    action: {
      resume: 'Reprendre',
      download: 'Télécharger',
      preview: 'Aperçu',
      report: 'Rapport',
    },
    report: {
      overview: 'Aperçu du rapport',
      loading: 'Chargement du rapport...',
      legend: {
        title: 'Légende du résumé du rapport',
        servicingToDrivingRatio: 'Ratio service/conduite',
        vehicleUtilizationRatio: "Taux d'utilisation des véhicules",
        averageTasksServicedPerShift: 'Moyenne des tâches effectuées par quart',
        averageTaskResponseTime: 'Temps moyen de réponse aux tâches',
        totalVehicleDistanceTravelled:
          'Distance totale parcourue par les véhicules',
      },
    },
    noResults: 'Aucun résultat.',
    previous: 'Précédent',
    next: 'Suivant',
    error: {
      loadTitle: 'Échec du chargement des simulations',
      loadPartial: 'Certaines simulations peuvent manquer dans la liste.',
      loadAll: 'Le chargement de toutes les simulations a échoué.',
      downloadReport: 'Erreur lors du téléchargement du rapport de simulation',
      previewReport:
        "Erreur lors du chargement de l'aperçu du rapport de simulation",
    },
  },
  map: {
    error: {
      loadTitle: 'Échec du chargement de la carte',
      loadDescription:
        'Une erreur est survenue lors du chargement de la carte. Veuillez réessayer plus tard.',
    },
    labels: {
      day: 'Jour',
      showAllRoutes: 'Afficher tous les trajets',
      tasksCount: 'Tâches ({{count}})',
      tasksSelectedCount: 'Tâches ({{selected}}/{{total}} sélectionnées)',
      taskSingular: 'tâche',
      taskPlural: 'tâches',
      stationsCount: '{{count}} stations ({{tasks}} tâches)',
      driverId: 'Chauffeur #{{id}}',
      stationId: 'Station #{{id}}',
      stationFallback: 'Station #{{id}}',
      noTasks: 'Aucune tâche',
      taskId: 'Tâche #{{id}}',
      servicing: 'En service',
    },
    assignment: {
      assign: 'Assigner',
      reassign: 'Réassigner',
      unassign: 'Désassigner',
      confirm: 'Confirmer',
      confirming: 'Confirmation...',
      assigning: 'Attribution...',
      remaining: 'Restantes ({{count}})',
      all: 'Toutes ({{count}})',
      batterySingular: 'batterie',
      batteryPlural: 'batteries',
      driverHasBatteries: '{{driver}} a {{count}} {{batteryWord}} restante(s).',
      assignTasksAnyway: '{{action}} {{count}} {{taskWord}} quand même?',
      alreadyAssigned:
        "({{count}} {{taskWord}} déjà assignée(s) à d'autres chauffeurs)",
      unassignSingle: 'Désassigner la tâche #{{taskId}} de {{driver}}?',
      reassignMultiFromTo: 'Réassigner {{count}} tâches de {{from}} à {{to}}?',
      reassignSingleFromTo:
        'Réassigner la tâche #{{taskId}} de {{from}} à {{to}}?',
      reassignMultiTo: 'Réassigner {{count}} tâches à {{to}}?',
      assignMultiTo: 'Assigner {{count}} tâches à {{to}}?',
      assignSingleTo: 'Assigner la tâche #{{taskId}} à {{to}}?',
    },
  },
  taskAssignmentBanner: {
    unassign: {
      single: {
        withStation:
          'Retirer la tâche #{{taskId}} à la station {{stationName}} assignée à {{driverName}}?',
        withoutStation:
          'Retirer la tâche #{{taskId}} assignée à {{driverName}} ?',
      },
      multi: {
        withStation:
          'Retirer les {{count}} tâches à la station {{stationName}} assignées à {{driverName}} ?',
        withoutStation:
          'Retirer les {{count}} tâches assignées à {{driverName}} ?',
      },
    },
  },
  driverStateBadge: {
    offShift: {
      label: 'Hors quart',
      short: 'Hors',
    },
    pendingShift: {
      label: 'Quart à venir',
      short: 'Attente',
    },
    idle: {
      label: 'Inactif',
      short: 'Inactif',
    },
    onRoute: {
      label: 'En route',
      short: 'Route',
    },
    servicing: {
      label: 'En service',
      short: 'Service',
    },
    onBreak: {
      label: 'En pause',
      short: 'Pause',
    },
    endingShift: {
      label: 'Fin de quart',
      short: 'Fin',
    },
    seekingHQForInventory: {
      label: 'Retour pour réapprovisionnement',
      short: 'Retour',
    },
    restockingBatteries: {
      label: 'Réapprovisionnement',
      short: 'Réappro.',
    },
  },
  simulation: {
    hqWidget: {
      allQuiet: 'Tout est calme au QG',
      driverSingular: 'chauffeur',
      driverPlural: 'chauffeurs',
      vehicleSingular: 'véhicule',
      vehiclePlural: 'véhicules',
      atHQ: 'au QG',
      noPendingShifts: 'Aucun quart en attente',
    },
  },
  diversity: {
    backToHome: "Retour à l'accueil",
    pageTitle: 'Déclaration sur la diversité',
    englishTab: 'Anglais',
    frenchTab: 'Français',
    commitmentTitleEn: 'Notre engagement',
    commitmentTitleFr: 'Notre engagement',
  },
  scenario: {
    editorTitle: 'Éditeur de scénario',
    dropToImport: 'Déposez pour importer un scénario',
    name: 'Nom du scénario',
    description: 'Description',
    descriptionPlaceholder: 'Saisir la description du scénario',
    jsonLabel: 'JSON du scénario',
    jsonPlaceholder: 'Collez ou saisissez votre scénario JSON ici...',
    import: 'Importer',
    new: 'Nouveau',
    edit: 'Modifier',
    export: 'Exporter',
    startSimulation: 'Démarrer la simulation',
    savedScenarios: 'Scénarios enregistrés',
    noSavedScenarios: 'Aucun scénario enregistré',
    deleteAriaPrefix: 'Supprimer',
    option: {
      addStation: 'Ajouter une station',
      addVehicle: 'Ajouter un véhicule',
      addDriver: 'Ajouter un chauffeur',
      useGbfsStations: 'Utiliser les stations GBFS',
    },
    toast: {
      station: 'Station',
      driver: 'Chauffeur',
      vehicle: 'Véhicule',
      addedSuccessfully: 'ajouté avec succès',
      gbfsFetchFailed:
        'Échec de récupération des informations de stations GBFS',
      gbfsLoaded: 'Stations GBFS chargées avec succès',
    },
    dialog: {
      simulationNameTitle: 'Nommez votre simulation',
      simulationNameDescription:
        'Donnez un nom à cette simulation pour la retrouver plus facilement.',
      simulationNameLabel: 'Nom de la simulation',
      simulationNamePlaceholder: 'Saisir le nom de la simulation',
      start: 'Démarrer',
      scenarioNameRequiredTitle: 'Nom du scénario requis',
      scenarioNameRequiredDescription:
        'Veuillez saisir un nom pour votre scénario pour continuer.',
      scenarioNameLabel: 'Nom du scénario',
      scenarioNamePlaceholder: 'Saisir le nom du scénario',
      continue: 'Continuer',
      overwriteTitle: 'Écraser ou Enregistrer comme Nouveau?',
      overwriteDescriptionPrefix: 'Vous modifiez le scénario',
      overwriteDescriptionSuffix:
        "Voulez-vous écraser le scénario existant ou l'enregistrer comme nouveau?",
      saveAsNew: 'Enregistrer comme Nouveau',
      overwrite: 'Écraser',
      unsavedChangesTitle: 'Modifications non enregistrées',
      unsavedChangesDescription:
        'Vous avez des modifications non enregistrées. Voulez-vous vraiment quitter? Vos modifications seront perdues.',
      discard: 'Ignorer',
      deleteTitle: 'Supprimer le scénario',
      deleteDescriptionPrefix: 'Voulez-vous vraiment supprimer',
      deleteDescriptionSuffix: 'Cette action est irréversible.',
      delete: 'Supprimer',
      addStationTitle: 'Ajouter une station',
      addStationDescription:
        'Configurez une nouvelle station à insérer dans le scénario.',
      stationNameLabel: 'Nom de la station',
      stationNamePlaceholder: 'ex. : Station rue Principale',
      latitudeLabel: 'Latitude',
      latitudePlaceholder: 'ex. : 45.5017',
      longitudeLabel: 'Longitude',
      longitudePlaceholder: 'ex. : -73.5673',
      scheduledTasksOptionalLabel: 'Tâches planifiées (optionnel)',
      scheduledTasksPlaceholder: 'ex. : day1:09:30, day1:14:00, day2:10:15',
      initialTaskCountOptionalLabel: 'Nombre initial de tâches (optionnel)',
      initialTaskCountPlaceholder: 'ex. : 5',
      addStationAction: 'Ajouter une station',
      addDriverTitle: 'Ajouter un chauffeur',
      addDriverDescription:
        'Configurez un nouveau chauffeur à insérer dans le scénario.',
      driverNameLabel: 'Nom du chauffeur',
      driverNamePlaceholder: 'ex. : Chauffeur 1',
      shiftStartTimeLabel: 'Heure de début du quart',
      shiftStartTimePlaceholder: 'ex. : day1:08:00',
      shiftEndTimeLabel: 'Heure de fin du quart',
      shiftEndTimePlaceholder: 'ex. : day1:17:00',
      lunchBreakOptionalLabel: 'Pause repas (optionnel)',
      lunchBreakPlaceholder: 'ex. : day1:12:00',
      addDriverAction: 'Ajouter un chauffeur',
      addVehicleTitle: 'Ajouter un véhicule',
      addVehicleDescription:
        'Configurez un nouveau véhicule à insérer dans le scénario.',
      vehicleNameLabel: 'Nom du véhicule',
      vehicleNamePlaceholder: 'ex. : Véhicule 1',
      latitudeOptionalLabel: 'Latitude (optionnel)',
      longitudeOptionalLabel: 'Longitude (optionnel)',
      batteryCountOptionalLabel: 'Nombre de batteries (optionnel)',
      batteryCountPlaceholder: 'ex. : 5',
      batteryCountHint:
        'Laissez vide pour démarrer au QG avec 0 batterie. Si une position est fournie, le véhicule démarre à cet emplacement.',
      addVehicleAction: 'Ajouter un véhicule',
    },
    validation: {
      driver: {
        nameRequired: 'Le nom du chauffeur est requis',
        startTimeRequired: "L'heure de début est requise",
        startTimeFormat:
          'Format invalide. Utilisez dayN:HH:MM (ex. : day1:08:00)',
        endTimeRequired: "L'heure de fin est requise",
        endTimeFormat:
          'Format invalide. Utilisez dayN:HH:MM (ex. : day1:17:00)',
        endAfterStart:
          "L'heure de fin doit être postérieure à l'heure de début",
        lunchFormat: 'Format invalide. Utilisez dayN:HH:MM (ex. : day1:12:00)',
        lunchBetween:
          'La pause repas doit être comprise entre le début et la fin du quart',
      },
      station: {
        nameRequired: 'Le nom de la station est requis',
        latitudeRequired: 'Une latitude valide est requise',
        latitudeRange: 'doit être comprise entre {{min}} et {{max}}',
        longitudeRequired: 'Une longitude valide est requise',
        longitudeRange: 'doit être comprise entre {{min}} et {{max}}',
        initialTaskNonNegative: 'Doit être un nombre non négatif',
        scheduledTaskFormat:
          'Format invalide : "{{task}}". Doit être dayN:HH:MM (ex. : day1:09:30)',
      },
      vehicle: {
        nameRequired: 'Le nom du véhicule est requis',
        insufficientDrivers:
          'Nombre insuffisant de chauffeurs pour un véhicule positionné',
        latitudeRequiredWhenLongitude:
          'La latitude est requise lorsque la longitude est fournie',
        latitudeRequired: 'Une latitude valide est requise',
        latitudeRange: 'doit être comprise entre {{min}} et {{max}}',
        longitudeRequiredWhenLatitude:
          'La longitude est requise lorsque la latitude est fournie',
        longitudeRequired: 'Une longitude valide est requise',
        longitudeRange: 'doit être comprise entre {{min}} et {{max}}',
        batteryNonNegative: 'Doit être un nombre non négatif',
      },
    },
    error: {
      loadScenariosTitle: 'Échec du chargement des scénarios',
      loadScenariosPartial: 'Certains scénarios peuvent manquer dans la liste.',
      loadScenariosAll: 'Le chargement de tous les scénarios a échoué.',
      importTitle: "Échec de l'importation",
      importDescription: "Le fichier n'est pas un scénario JSON valide.",
      noScenarioTitle: 'Aucun scénario',
      noScenarioDescription:
        'Veuillez créer ou charger un scénario avant de démarrer la simulation.',
      invalidTitle: 'Scénario invalide',
      invalidDescription: 'Format JSON invalide',
      noContentToProcessTitle: 'Aucun contenu à traiter',
      noContentToProcessDescription:
        "Veuillez saisir ou charger un scénario d'abord.",
      invalidJsonTitle: 'Format JSON invalide',
      invalidJsonDescription:
        "Le contenu du scénario n'est pas un JSON valide. Veuillez corriger le formatage.",
      validationFailedTitle: 'La validation du scénario a échoué',
      validationTitle: 'Erreur de validation',
      downloadFailedTitle: 'Échec du téléchargement',
      downloadFailedDescription:
        'Une erreur inattendue est survenue lors du téléchargement du fichier. Veuillez réessayer.',
      noContentToSaveTitle: 'Aucun contenu à enregistrer',
      noContentToSaveDescription: "Veuillez d'abord saisir un scénario.",
      saveFailedTitle: "Échec de l'enregistrement du scénario",
      overwriteFailedTitle: "Échec de l'écrasement du scénario",
      deleteFailedTitle: 'Échec de la suppression du scénario',
      initializeTitle: "Échec de l'initialisation",
      unableToLoadTitle: 'Impossible de charger le scénario',
      unableToLoadDescription:
        "Le scénario n'a pas pu être analysé comme JSON.",
    },
  },
} as const satisfies TranslationSchema;
