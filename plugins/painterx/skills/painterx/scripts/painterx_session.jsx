(function () {
  if (typeof PAINTERX_PLAN === "undefined") return "ERROR|Missing PAINTERX_PLAN";

  var plan = PAINTERX_PLAN;

  function writeJson(path, value) {
    var file = new File(path);
    file.encoding = "UTF-8";
    if (!file.open("w")) throw new Error("Could not write progress file: " + path);
    var fields = [];
    for (var key in value) {
      if (!value.hasOwnProperty(key)) continue;
      var item = value[key];
      if (typeof item === "number" || typeof item === "boolean") fields.push('"' + key + '":' + item);
      else fields.push('"' + key + '":"' + String(item).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/[\r\n]/g, " ") + '"');
    }
    file.write("{" + fields.join(",") + "}");
    file.close();
  }

  function valueOf(result, key) {
    var parts = String(result).split("|");
    for (var index = 0; index < parts.length; index += 1) {
      if (parts[index].indexOf(key + "=") === 0) return parts[index].substring(key.length + 1);
    }
    return null;
  }

  function invoke(configuration) {
    CELL_LCT_CACHED_CONFIG = configuration;
    return String($.evalFile(new File(plan.runtimePath)));
  }

  function fail(message, completed, batchIndex) {
    writeJson(plan.progressPath, {
      ok: false,
      completed: completed,
      failed_batch: batchIndex,
      message: String(message)
    });
    return "ERROR|completed=" + completed + "|failed_batch=" + batchIndex + "|" + message;
  }

  try {
    if (app.documents.length < 1) return fail("AI_DOCUMENT_REQUIRED", 0, -1);
    if (parseFloat(app.version) < plan.minimumIllustratorMajor) {
      return fail("ILLUSTRATOR_VERSION_UNSUPPORTED|version=" + app.version, 0, -1);
    }

    var targetDocumentName = app.activeDocument.name;
    var completed = 0;
    for (var batchIndex = 0; batchIndex < plan.batches.length; batchIndex += 1) {
      var batch = plan.batches[batchIndex];
      var result = invoke({
        operation: "draw",
        batchJsonPath: batch.batchJsonPath,
        targetDocumentName: targetDocumentName,
        rootGroupName: plan.rootGroupName,
        batchGroupName: batch.groupName,
        placement: plan.placement,
        maxWidthFraction: plan.maxWidthFraction,
        maxHeightFraction: plan.maxHeightFraction,
        delayMs: plan.delayMs,
        targetLayerName: plan.targetLayerName
      });
      if (result.indexOf("OK|") !== 0) return fail(result, completed, batchIndex);
      completed += 1;
      writeJson(plan.progressPath, {ok: true, completed: completed, total: plan.batches.length});

      if (plan.outputAi && (completed === 1 || completed % plan.checkpointEveryBatches === 0)) {
        result = invoke({operation: "save", targetDocumentName: targetDocumentName, outputAi: plan.outputAi});
        if (result.indexOf("OK|") !== 0) return fail("CHECKPOINT_FAILED|" + result, completed, batchIndex);
        targetDocumentName = valueOf(result, "documentName") || targetDocumentName;
      }
    }

    var result = invoke({
      operation: "normalize",
      targetDocumentName: targetDocumentName,
      rootGroupName: plan.rootGroupName,
      batchGroupNames: plan.batchGroupNames
    });
    if (result.indexOf("OK|") !== 0) return fail("NORMALIZE_FAILED|" + result, completed, -1);

    result = invoke({
      operation: "qa",
      targetDocumentName: targetDocumentName,
      rootGroupName: plan.rootGroupName,
      batches: plan.qaBatches
    });
    if (result.indexOf("OK|missing=0|placed=0|raster=0") !== 0) {
      return fail("QA_FAILED|" + result, completed, -1);
    }

    if (plan.outputAi) {
      result = invoke({operation: "save", targetDocumentName: targetDocumentName, outputAi: plan.outputAi});
      if (result.indexOf("OK|") !== 0) return fail("FINAL_SAVE_FAILED|" + result, completed, -1);
      targetDocumentName = valueOf(result, "documentName") || targetDocumentName;
    }
    if (plan.outputPng) {
      result = invoke({operation: "export", targetDocumentName: targetDocumentName, outputPng: plan.outputPng});
      if (result.indexOf("OK|") !== 0) return fail("EXPORT_FAILED|" + result, completed, -1);
      // Illustrator 2021 marks the document modified after PNG export. Save
      // once more so an explicitly requested export leaves a clean AI file.
      if (plan.outputAi) {
        result = invoke({operation: "save", targetDocumentName: targetDocumentName, outputAi: plan.outputAi});
        if (result.indexOf("OK|") !== 0) return fail("POST_EXPORT_SAVE_FAILED|" + result, completed, -1);
      }
    }

    writeJson(plan.progressPath, {ok: true, completed: completed, total: plan.batches.length, finished: true});
    return "OK|completed=" + completed + "|documentName=" + targetDocumentName;
  } catch (error) {
    return fail(error.message + "|line=" + error.line, 0, -1);
  }
}());
