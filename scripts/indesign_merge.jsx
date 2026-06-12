#target indesign
/*
 * ABE Visitenkarten – InDesign Data-Merge Export
 * --------------------------------------------------------------------------
 * Nimmt die vom Tool erzeugte Datenquelle (UTF-16, Tab-getrennt), verknüpft
 * sie mit der Master-Vorlage und exportiert in EINEM Schritt:
 *   - ein Proof-PDF (niedrige Auflösung) für die Freigabe
 *   - ein Druck-PDF (hohe Auflösung, PDF/X) für die Partnerdruckerei
 *
 * Verwendung: in InDesign über das Skripte-Bedienfeld doppelklicken.
 * Die vier KONFIG-Zeilen unten anpassen (Pfade + PDF-Vorgaben).
 *
 * Hinweis: Bitte einmal in eurer InDesign-Version testen und die Namen der
 * PDF-Vorgaben ([Smallest File Size], [PDF/X-1a:2001]) ggf. an eure
 * Joboptions anpassen.
 */
(function () {
    // ---- KONFIG --------------------------------------------------------------
    var MASTER  = "~/ABE/VK-Barmag-Master.indd";  // Pfad zur Master-Vorlage
    var DATEN   = "~/ABE/merge_Barmag.txt";        // vom Tool erzeugte Datenquelle
    var AUSGABE = "~/ABE/ausgabe";                 // Zielordner für die PDFs
    var BASIS   = "VK_Barmag";                      // Basis des Dateinamens
    var PRESET_PROOF = "[Smallest File Size]";      // Proof = niedrige Auflösung
    var PRESET_DRUCK = "[PDF/X-1a:2001]";           // Druck = hohe Auflösung
    // --------------------------------------------------------------------------

    var master = File(MASTER);
    if (!master.exists) { alert("Master-Vorlage nicht gefunden:\n" + MASTER); return; }
    var daten = File(DATEN);
    if (!daten.exists) { alert("Datenquelle nicht gefunden:\n" + DATEN); return; }
    var ziel = Folder(AUSGABE);
    if (!ziel.exists) { ziel.create(); }

    var doc = app.open(master);

    // Datenquelle verknüpfen
    doc.dataMergeProperties.selectDataSource(daten);

    // Alle Datensätze berücksichtigen
    try {
        doc.dataMergeProperties.dataMergePreferences.recordSelection = RecordSelection.ALL_RECORDS;
    } catch (e) {}

    // "In PDF exportieren" = zusammenführen + exportieren in einem Rutsch
    function exportPDF(presetName, suffix) {
        var preset = app.pdfExportPresets.itemByName(presetName);
        if (!preset.isValid) { alert("PDF-Vorgabe nicht gefunden:\n" + presetName); return; }
        var out = File(ziel.fsName + "/" + BASIS + "_" + suffix + ".pdf");
        doc.dataMergeProperties.exportFile(out, false, preset);
    }

    exportPDF(PRESET_PROOF, "proof");
    exportPDF(PRESET_DRUCK, "druck");

    doc.close(SaveOptions.NO);
    alert("Fertig. PDFs liegen in:\n" + ziel.fsName);
})();
