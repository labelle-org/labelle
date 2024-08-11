# Calibration Wizard

In case the user's printer model isn't supported by Labelle yet, or for any other reason, Calibration Wizard may enable the user to generate their own calibration data.

This will enpower the users to take a more active role in Labelle development, and most importantly let them use Labelle without waiting for a new release supporting their device.



## Workflow

The calibration must be an easy and accessible process, possibly accompanied by photos. The general workflow could look like this:

1. Briefly explain the process, confirm they're ready to continue,

2. Print test pattern with setting 512

3. Ask the user for the lowest and highest visible rows of dots,

4. Print test pattern again, including calibration data,

5. Confirm the results are satisfying, if not -> abort

6. Save calibration data, possibly within the source file itself

7. Encourage the user to share their results on Github



## 1. Introduction / expalantion

In the command line and GUI alike, a message should be shown to explain to the user what they're going to achieve with this wizard.

Something like:

> This calibration wizard is designed to adjust printing parameters to your combination of printer and tape cartridge. If you experienced clipping or offsets on your label prints, chances are that the maintainers of Labelle did not implement support for your hardware yet. This tool will guide you through a calibration process.
> 
> Remember that the calibration data is only valid per printer model AND cartridge size. If you own more than one cartridge size, the process should be repeated for every one of them.
> 
> If your device is ready for use, press [something] to continue.

## 2. Print the test pattern

The test pattern should be printed with parameter 512 (more than enough for any printer we've seen so far), and ignoring all offsets imposed by the existing user or hardcoded calibration data. Currently this is the default behavior of this function.

## 3. Ask for feedback

This is the crucial step for the success of the process. The user is expected to type in the numbers of the lowermost and highermost visible lines. The input data need to be checked for their sanity.

Here's a draft of the message displayed to a user:

> The printer have printed a test pattern. Analyze it carefully. 
> 
> The test pattern consists of dot lines enumerated from the bottom edge to the top edge. For your convenience, the first line counting from the bottom has number 1.
> 
> Please provide numbers of the lowest and highest visible lines.
> 
> If you have trouble interpreting the test pattern, please consult a detailed manual [here]([labelle/doc/margin-calibration-howto.md at main · labelle-org/labelle · GitHub](https://github.com/labelle-org/labelle/blob/main/doc/margin-calibration-howto.md#determining-the-height-of-the-print-head)).

At this point the algorithm should check whether:

- None of the fields is empty,

- Provided numbers are integers > 0,

- the lowest line number is lower than highest line number,

- The difference between the two is within (32 : 512) range

If any of these tests fails, an appropriate message should be shown, and the user has to have a chance to type the values again.

If the values are correct, store them in the following way:

- Lowermost line number minus one is the new offset,

- The difference between the two is what I used to call "canvas height".

## 4. Repeat test print with new calibration data

This step will ensure that the calibration data is indeed correct.

The test pattern should be printed including the offset and height calculated in the previous step.

Offset translates to adding empty lines to the bottom of the bitmap, and height is the test pattern parameter.

## 5. Confirm the results with the user

Display the message to the user:

> Your printer has printed a new test pattern including your previous feedback. Please confirm that the whole test pattern is visible.
> 
> Specifically, each test pattern begins and ends with 10 interleaved, horizontal lines. Make sure that all of them are visible, on the top and bottom of your test print.

Collect the answer and act accordingly:

- Store data and move on to the next point, or

- Abandon the process.

## 6. Save calibration data

This is left to the implementer's discretion. Either this could be added directly to the source file (which might not be the brightest idea due to write permissions), or stored in user's `~/.config/labelle/user_calibration` file. This should work just fine until we start supporting non-Unix OSes.

From this point, Labelle should of course read and parse this file, and treat it with higher priority than hardcoded data.

## 7. Thank the user for cooperation

Display the following message:

> Please consider sharing your calibration data with Labelle community, so it may be included in future releases of Labelle. To do so, file an issue in our GitHub repository ([Issues · labelle · GitHub](https://github.com/labelle-org/labelle/issues)) and include your user calibration data file, which can be found at `/home/{user}/.config/labelle/user_calibration`.
> 
> Thank you!
