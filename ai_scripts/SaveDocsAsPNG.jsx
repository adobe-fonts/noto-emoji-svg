/**********************************************************

ADOBE SYSTEMS INCORPORATED
Copyright 2005-2006 Adobe Systems Incorporated
All Rights Reserved

NOTICE:  Adobe permits you to use, modify, and
distribute this file in accordance with the terms
of the Adobe license agreement accompanying it.
If you have received this file from a source
other than Adobe, then your use, modification,
or distribution of it requires the prior
written permission of Adobe.

*********************************************************/

/**	Saves every document open in Illustrator
	as an PNG file in a user specified folder.
*/

// Main Code [Execution of script begins here]

// uncomment to suppress Illustrator warning dialogs
// app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;

try {
	if (app.documents.length > 0 ) {

		// Get the folder to save the files into
		var destFolder = null;
		destFolder = Folder.selectDialog( 'Select folder for PNG files.', '~' );

		if (destFolder != null) {
			var options, targetFile;

    		// Get the PNG options to be used.
			options = this.getOptions();
    		// You can tune these by changing the code in the getOptions() function.

			var doc_count = 0;
			while (app.documents.length) {
				var aiDocument = app.activeDocument;

				// Get the file to save the document as PNG into
				targetFile = this.getTargetFile(aiDocument.name, '.png', destFolder);

				// Save as PNG
				aiDocument.exportFile(targetFile, ExportType.PNG24, options);

				doc_count ++;

				// Close current document
				aiDocument.close(SaveOptions.DONOTSAVECHANGES);
			}
			alert( doc_count + ' documents saved as PNG to\r' + destFolder );
		}
	}
	else{
		throw new Error('There are no document open!');
	}
}
catch(e) {
	alert( e.message, "Script Alert", true);
}


/** Returns the options to be used for the generated files.
	@return ExportOptionsPNG24 object
*/
function getOptions() {
	// Create the required options object
	var options = new ExportOptionsPNG24();
	// See ExportOptionsPNG24 in the JavaScript Reference for available options

	var rgb_color = new RGBColor();
	rgb_color.red = 255;
	rgb_color.green = 255;
	rgb_color.blue = 255;

	// Set the options you want below:
	options.antiAliasing = true;
	options.artBoardClipping = true;
	options.horizontalScale = 100.0;
	options.verticalScale = 100.0;
	options.matte = true;
	options.matteColor = rgb_color;
	options.saveAsHTML = false;
	options.transparency = true;

	return options;
}

/** Returns the file to save or export the document into.
	@param docName the name of the document
	@param ext the extension the file extension to be applied
	@param destFolder the output folder
	@return File object
*/
function getTargetFile(docName, ext, destFolder) {
	var newName = "";

	// if name has no dot (and hence no extension),
	// just append the extension
	if (docName.indexOf('.') < 0) {
		newName = docName + ext;
	} else {
		var dot = docName.lastIndexOf('.');
		newName += docName.substring(0, dot);
		newName += ext;
	}

	// Create the file object to save to
	var myFile = new File( destFolder + '/' + newName );

	// Preflight access rights
	if (myFile.open("w")) {
		myFile.close();
	}
	else {
		throw new Error('Access is denied');
	}
	return myFile;
}
