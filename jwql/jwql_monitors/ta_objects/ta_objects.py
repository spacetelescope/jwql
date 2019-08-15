import numpy as np
import pysiaf

# PostageStamp class and class functions

class PostageStamp(dict):

    def __init__(self, data_cube, flat_image, stamp_params, exposure_params, ta_params, *args, **kwargs):
        '''Create postage stamp object and add selected scalars and images as fields of object for later analysis.
        Includes gentalocate to find centroid of target in postage stamp, and ta_transforms to convert measured 
        row and column to V2, V3 coordinates
        inputs:
            data_cube - 3 group image of one detector from TA exposure
            flat_image - TA flat image for detector in data_cube
            stamp_params - dictionary with parameters unique to each postage stamp
                required fields for Postage Stamp init function:
                    refstar_no
                    col_corner_stamp
                    row_corner_stamp
                    detector 
            ta_params - dictionary with parameters that will stay constant for all postage stamps in a given TA
                required fields for Postage Stamp init function:
                    col_start -  full frame column coordinates of 1st pixel in data_cube, =1 for full frame 
                    row_start -  full frame row coordinates of 1st pixel in data_cube, =1 for full frame 
                    extract_cols - size of postage stamp to be extracted from image in col direction
                    extract_rows - size of postage stamp to be extracted from image in row direction
                    check_box_size
                    background_method - background subtraction after flatfielding if = 'FRACTION'
                    backgroud_value - percentile of image to be taken as background level
                    ref_level_method - background (reference) subtraction after slope difference if = 'FRACTION'
                    ref_level_vaules - percentile of image  to be taken as reference level
        Outputs:
            A PostageStamp object is produced
            Fields critical for further TA analysis are added to the object by the init function.
            Other fields useful for diagnostic purposes are added by self._gentalocate, but these are not
            critical for the primary use of this object in analysing a TA
        Critical output fields added to object by init function-
            all fields in stamp_params dictionary (information unique to each postage stamp)
            .col_center - measured column centroid position found for the reference star
            .row_center
            .v2_measured
            .v3_ending
        other fields added by _gentalocate which is called by __init__ 
        (These are not critical to TA calculations, but can be useful for later analysis and reporting)
            
        '''
        
        super().__init__(*args, **kwargs)
        
        # need to add function to check stamp_params and ta_params for required fields!!!   
        
        # store all parameter dictionaries as fields
        self.update(exposure_params)
        self.update(stamp_params)
        self.update(ta_params)

        self._gentalocate(data_cube, flat_image)
        self._ta_transforms()

    #Add dot access for dictionary items
    def __getattr__(self, key):
        return self[key]
        
    def __setattr__(self, key, value):
        self[key] = value
    
    #Convenience properties to convert row & col to 1-base
    @property
    def col_center_onebase(self):
        return self.col_center + 1
    
    @property
    def row_center_onebase(self):
        return self.row_center + 1
    
    @property
    def col_locate_onebase(self):
        return self.col_locate + 1

    @property
    def row_locate_onebase(self):
        return self.row_locate + 1

    def _ta_transforms(self):
        '''Transform measured centroid location to measured V2/V3 
        Inputs:
          col_center - measured column centroid in 0-based coordinates of PostageStamp image
          row_center - measured row centroid in 0-based coordinates of PostageStamp image
          stamp_params - needed following quantities from this dictionary
              col_corner_stamp
              row_corner_stamp
              v2_desired
              v3_desired
        creates attributes:
              Measured v2 and v3 location of target
              SIAF X, Y predicted from desired V2/V3 location
        '''

        nrs_siaf = pysiaf.Siaf('NIRSpec')
        if self.detector in ['NRS1', 1]:
            aperture = nrs_siaf['NRS1_FULL_OSS']
        else:
            aperture = nrs_siaf['NRS2_FULL_OSS']
        aperture.tilt = (self.gwa_x_tilt, self.gwa_y_tilt)
        aperture.filter_name = self.filter_name
        x_siaf_det = self.row_center + self.row_corner_stamp
        y_siaf_det = self.col_center + self.col_corner_stamp
    
        self.v2_measured, self.v3_measured = aperture.det_to_tel(x_siaf_det, 
                                                                 y_siaf_det)
        
        self.x_siaf_expected, self.y_siaf_expected = aperture.tel_to_det(self.v2_desired, 
                                                                         self.v3_desired)
        
    def _gentalocate(self, data_cube, flat_image):
        '''Find centroid of target in a PostageStamp image
           inputs: 
             data_cube - 3 group TA image
             flat_image - TA flat image for the same detector as the data_cube
             stamp_params -
             ta_params -
          creates attributes:
             col_center - measured column centroid in 0-based coordinates of PostageStamp image
             row_center - measured row centroid in 0-based coordinates of PostageStamp image
             centroid_success - True if centroid found, False if too close to edge or iteration did not converge
          Also saves selected quantities and images as fields in the PostageStamp object.
        '''
        
        self._get_stamp(data_cube)
        self._slope_diff()
        self._cosmic_ray()        
        self._extract_flat(flat_image)
        self._flatfield()
        self._subtract_background()
        
        self._find_bright_checkbox()
        self._centroid_2d()

        # full frame one-based coordinates
        self.row_detector_center = self.row_center + self.row_corner_stamp
        self.col_detector_center = self.col_center + self.col_corner_stamp
        
    def _get_stamp(self, data_cube):
        """
        Assign the 3 groups in the postage stamp to the self.groups attribute.
        """
        cs = slice(self.col_corner_stamp - self.col_start, 
                   self.col_corner_stamp - self.col_start + self.extract_cols)
        rs = slice(self.row_corner_stamp - self.row_start, 
                   self.row_corner_stamp - self.row_start + self.extract_rows)
        self.groups = data_cube[:3, rs, cs] #not sure if this is ever more than 3? if not, can replace ':3' with ':'
    
    def _slope_diff(self):
        self.slope1, self.slope2 = self.groups[1:].astype(np.float32) - self.groups[:2].astype(np.float32)
    
    def _cosmic_ray(self):
        '''rejects cosmic rays by taking the minimum of each pixel in the two input images,
       clipping any negative values to zero
       inputs:
         slope1, slope2 - difference images from image groups
       output:
         uint16 image, with minumum of input images
       optional: 
         allows for an extra background subtraction of the difference images to be done
         before taking the minimum at each pixel if 'ref_level_method' it ta_params set 
         to "FRACTION", but OSS does NOT include any such option
        '''
        if(self.ref_level_method == 'FRACTION'):
            ref1 = self._bkg_value(self.slope1, self.ref_value)
            ref2 = self._bkg_value(self.slope2, self.ref_value)
            print(ref1, ref2)
        else:
            ref1 = 0
            ref2 = 0
        crj = np.minimum(self.slope1 - ref1, self.slope2 - ref2).astype(np.int32)
        self.crj = np.clip(crj, a_min=0, a_max=np.uint16(-1)).astype(np.uint16)
    
    def _extract_flat(self, full_flat_image):
        '''Get portion of flat field image aligned with current PostageStamp'''
        cc = self.col_corner_stamp - 1
        rc = self.row_corner_stamp - 1025
        self.stamp_flat = full_flat_image[rc: rc + self.extract_rows, cc: cc + self.extract_cols]

    def _flatfield(self):
        scale_factor = 1000
        bad_value = np.uint16(-1)
        big_value = float(np.uint32(-1))
        
        flattened_image = np.round(np.float32(self.crj) * (np.float32(self.stamp_flat) / scale_factor))
        flattened_image[self.stamp_flat == bad_value] = big_value
        self.fixed_image = self._fixpix(flattened_image)        

    def _fixpix(self, input_image):
        '''Replace bad pixels in postage stamp with median of neighboring pixels
        inputs:
            input_image - 2d array
            stamp_flat - 2d array where value = 65535 identifies bad pixel
            ta_params - needs ta_params.extract_cols & ta_params.extract_rows
        outputs:
            array with pixels in input_image flagged as bad in stamp_flat replaced by median of their neighbors
            
        1st takes median of nearest 4 neighbors, clipping those outside postage stamp, 
        but if 1/2 or more of these are also "bad" takes median of nearest 8. 
        If 1/2 or more still bad, then set pixel to default value.
        '''

        bad_value = np.uint16(-1)
        default_value = 0
        
        new_image = input_image.copy()
        
        if np.count_nonzero(self.stamp_flat == bad_value) == 0:
            return new_image.copy()
        
        row_bad, col_bad = (self.stamp_flat == bad_value).nonzero()
        nbad = row_bad.size

        # need to sort bad pix so we do replacement in row order, and in column order for pixels in same row
        iorder = np.argsort(row_bad + col_bad/self.extract_cols)
        row_bad = row_bad[iorder]
        col_bad = col_bad[iorder]

        for bad_pix_index in np.arange(nbad):
            row = row_bad[bad_pix_index]
            col = col_bad[bad_pix_index]

            row_neighbors, col_neighbors = self._fixpix_pattern(row, col, 0)
            new_value = np.median(new_image[row_neighbors, col_neighbors])
            if((new_value >= bad_value) | (new_value < 0)):
                row_neighbors, col_neighbors = self._fixpix_pattern(row, col, 1)
                new_value = np.median(new_image[row_neighbors, col_neighbors])
                if((new_value >= bad_value) | (new_value < 0)):
                    new_value = default_value
            new_image[row, col] = new_value
        return(new_image)
    
    def _fixpix_pattern(self, row, col, ipattern):
        '''Find pixels to be used for median replacement of bad pixel, using one of two specified patterns
        for selection of neighbors, but discarding locations outside of postage stamp
        inputs: 
            row - row number of bad pixel in local coordinates of postage stamp
            col - col number of bad pixel
            ipattern - 0 for simple cross pattern, 1 to check whole ring around pixel
            ta_params - target acquistion parameters
                      - need ta_params['extract_cols'] and ta_params['extract_rows'] to give size of 
                        postage stamp
            returns
               row_pat, col_pat (row and column locations of pixels to be used for median replacement)
        '''
        
        col_size = self.extract_cols
        row_size = self.extract_rows
        
        if(ipattern == 0):
            col_neighbors = col + np.array([-1, 0, 0, 1])
            row_neighbors = row + np.array([0, -1, 1, 0])
        elif(ipattern == 1):
            col_neighbors = col + np.array([-1, 0, 0, 1, 1, 1, -1, -1])
            row_neighbors = row + np.array([0, -1, 1, 0, -1, 1, -1, 1])
        keep = (col_neighbors >= 0) & (row_neighbors >= 0) & (col_neighbors < col_size) & (row_neighbors < row_size)
        return(row_neighbors[keep], col_neighbors[keep])
        
    
    def _bkg_value(self, image, value):
        '''Find kth smallest pixel in sorted array, where k = int(background_value * npixels) 
        inputs:
          image - array of values
          background_value - fractional of pixels to be fainter than measured background_measured
        returns:
          measured background value of kth smallest pixel
        '''        
        sorted_list = np.sort(np.ndarray.flatten(image))
        return(sorted_list[int(value * np.size(sorted_list))])
    
    def _subtract_background(self):
        print(self.background_method)
        if(self.background_method == 'FRACTION'):
            self.bkg_measured = self._bkg_value(self.fixed_image, self.background_value)            
        else:
            self.bkg_measured = 0
        out_image = self.fixed_image.copy() - self.bkg_measured
        self.bkg_subtracted = np.clip(out_image, a_min=0, a_max=None)
    
    def _find_bright_checkbox(self):
        '''find brightest checkbox in image 
         inputs:
          image - 2D image with flux values with dimensions extract_rows & extract_cols
          ta_params - dictionary with adjustable TA parameters
             here we need the 'check_box_size' which gives the size of the checkbox to be summed over
             and 'extract_rows' and 'extract_cols' giving the dimensions
         returns: 
           column and row of checkbox center with highest summed counts, plus value of that sum
           note coordinates of the checkbox center returned are zero-based coordinates of the input image
        '''
        hwidth = int(self.check_box_size / 2)
        extract_rows = self.extract_rows
        extract_cols = self.extract_cols
        #extract_rows, extract_cols = np.shape(image)
        
        bright_value = -99
        col_bright = 0
        row_bright = 0
        
        for icol in hwidth + np.arange(extract_cols - 2 * hwidth):
            for irow in hwidth + np.arange(extract_rows - 2 * hwidth):
                box_value = np.sum(self.bkg_subtracted[irow - hwidth: irow + hwidth + 1, icol - hwidth: icol + hwidth + 1])
                if(box_value > bright_value):
                    bright_value = box_value
                    col_bright = icol
                    row_bright = irow
        self.col_locate, self.row_locate, self.checkbox_flux = (col_bright, 
                                                                row_bright, 
                                                                bright_value)
        
    def _centroid_2d(self, debug=False):
        '''Do sub-pixel centroid of TA star in a postage stamp
        Note that this works in 0-based coordinates of the postage stamp. If one based coordinates are needed,
        adjustment is necessary.
        Inputs:
           image - 2D postage stamp image of references star used for TA
           col_initial - initial estimate of column position from _find_bright_checkbox
           row_initial - initial estimate of row position from _find_bright_checkbox
           ta_params - dictionary with needed parameters to control TA algorithm
        Outputs:
            New centroid row location in image
            New centroid column location
            Centroid flux measurement
            Boolean value with centroid success status
        '''
        col_half_width = self.centroid_num_cols / 2.0
        row_half_width = self.centroid_num_rows / 2.0
        image_row_size = self.extract_rows
        image_col_size = self.extract_cols
        max_iterations = self.centroid_max_iterations
        convergence_threshold = self.convergence_thresh
        # set initial "error" to 1/2 of locate box size
        delta_col = delta_row = self.check_box_size / 2

        col_center_last = self.col_locate
        row_center_last = self.row_locate
        self.centroid_success = None
        iteration = 0
        
        while (self.centroid_success is None):
            iteration += 1
            # centroid box edges in fractional pixels, clipped to postage stamp edges
            edge_lft = max(col_center_last - col_half_width, 0)
            edge_rgt = min(col_center_last + col_half_width, image_col_size - 1)
            edge_bot = max(row_center_last - row_half_width, 0)
            edge_top = min(row_center_last + row_half_width, image_row_size - 1)
            
            #integer indices of pixels that include edges
            pix_lft = max(int(np.floor(edge_lft + 0.5)), 0)
            pix_rgt = min(int(np.floor(edge_rgt + 0.5)), image_col_size - 1)
            pix_bot = max(int(np.floor(edge_bot + 0.5)), 0)
            pix_top = min(int(np.floor(edge_top + 0.5)), image_row_size - 1)
            
            pix_size_col = pix_rgt - pix_lft + 1
            pix_size_row = pix_top - pix_bot + 1
            
            weights = np.ones((pix_size_row, pix_size_col))
            # weight edge pixels by fraction included in centroid box
            weights[:, 0] = weights[:, 0] * (pix_lft + 0.5 - edge_lft)
            weights[:, pix_size_col - 1] = weights[:, pix_size_col - 1] * (1 - (pix_rgt + 0.5 - edge_rgt))
            weights[0, :] = weights[0, :] * (pix_bot + 0.5 - edge_bot)
            weights[pix_size_row - 1, :] = weights[pix_size_row - 1, :] * (1 - (pix_top + 0.5 - edge_top))
            
            col_numbers = pix_lft + np.tile(np.arange(pix_size_col), (pix_size_row, 1))
            row_numbers = pix_bot + np.transpose(np.tile(np.arange(pix_size_row), (pix_size_col, 1)))
            
            sub_image = self.bkg_subtracted[pix_bot: pix_top + 1, pix_lft: pix_rgt + 1]
            flux_sum = np.sum(weights * sub_image)
            if(flux_sum <= 0):
                self.col_center, self.row_center = col_center_last, row_center_last
                self.centroid_flux = flux_sum
                self.centroid_success = False
                return
            col_center_new = np.sum(col_numbers * weights * sub_image) / flux_sum
            row_center_new = np.sum(row_numbers * weights * sub_image) / flux_sum
            
            delta_col = col_center_new - col_center_last
            delta_row = row_center_new - row_center_last            
            col_center_last = col_center_new
            row_center_last = row_center_new

            # fail if too close to edge
            if ((col_center_last - col_half_width < 0) 
                    | (row_center_last - row_half_width < 0)
                    | (col_center_last + col_half_width >= image_col_size)
                    | (row_center_last + row_half_width >= image_row_size)):
                self.centroid_success = False
            #Success if both axes converged
            elif (abs(delta_col) < convergence_threshold) & (abs(delta_row) < convergence_threshold):
                self.centroid_success = True
            # fail if out of interations and not yet converged
            elif iteration > max_iterations:
                self.centroid_success = False
        
        if debug:
            print(sub_image)
            print(weights)
            print(col_numbers)
            print(row_numbers)
            print(flux_sum)
            print(col_center_last, row_center_last)
            print(edge_bot, edge_top, edge_lft, edge_rgt)
            print(pix_bot, pix_top, pix_lft, pix_rgt)
        
        self.col_center, self.row_center = col_center_last, row_center_last
        self.centroid_flux = flux_sum
        
# following class functions are intended for use after object has been created
    
    def stamp_results(self):
        '''produce text summary of gentalocate and tatransforms results'''
        
        output_string = """Reference Star Input Parameters
        (col corner, row corner) {col_corner_stamp} {row_corner_stamp}
        8218: Detector = {detector}
        (v2_desired, v3_desired) {v2_desired:+.6f} {v3_desired:+.6f}
        
        GENTALOCATE Results Summary
        8215: Measured background: {bkg_measured}
        8214: postage Stamp centroid (col, row, flux: ) {col_center_onebase:.6f} {row_center_onebase:.6f} {centroid_flux:.3f}
        8221: detector Stamp centroid (col, row, success: ) {col_detector_center:.6f} {row_detector_center:.6f} {centroid_success}
        
        TA Transforms Results Summary
        (v2_measured, v3_measured) {v2_measured:+.6f} {v3_measured:+.6f}
        (y_siaf_expected, x_siaf_expected) {y_siaf_expected:.6f} {x_siaf_expected:.6f}

        """
        return output_string.format(**self)
    
    @property
    def table_output(self):
        """
        Condense the postage stamp information into a single data structure 
        which can be stored in a database. This must contain sufficient info
        to allow Bokeh to reconstruct the postage stamp for user interaction:
            
            refstar_no
            v2_desired, v3_desired
            detector
            col_corner_stamp, row_corner_stamp
            gwa_x_tilt, gwa_y_tilt
            bkg_measured
            col_locate_onebase, row_locate_onebase
            checkbox_flux
            col_center_onebase, row_center_onebase
            centroid_flux
            col_detector_center, row_detector_center
            centroid_success
            v2_measured, v3_measured
            y_siaf_expected, x_siaf_expected
            extent: slope1, slope2, crj, bkg_subtracted, stamp_flat
            arrays: slope1, slope2, crj, bkg_subtracted, stamp_flat
        """
        fieldnames = ['slope1', 'slope2', 'crj', 'bkg_subtracted', 'stamp_flat']
        rowsize, colsize = zip(*[self[field].shape for field in fieldnames])
        col_lft = np.array([self.col_corner_stamp] * 5) - 0.5
        col_rgt = col_lft + np.array(colsize) + 1
        row_bot = np.array([self.row_corner_stamp] * 5) - 0.5
        row_top = row_bot + np.array(rowsize) + 1
        extents = dict(zip(['extent_'+ field for field in fieldnames], 
                           zip(col_lft, col_rgt, row_bot, row_top)))
        
        output = {
                'refstar_no': int(self.refstar_no),
                'v2v3_desired': [self.v2_desired, self.v3_desired],
                'detector': self.detector,
                'corner_stamp': [self.col_corner_stamp, self.row_corner_stamp],
                'gwa_tilt': [self.gwa_x_tilt, self.gwa_y_tilt],
                'bkg_measured': self.bkg_measured,
                'locate_onebase': [self.col_locate_onebase, 
                                   self.row_locate_onebase],
                'checkbox_flux': self.checkbox_flux,
                'center_onebase': [self.col_center_onebase,
                                   self.row_center_onebase],
                'centroid_flux': self.centroid_flux,
                'detector_center': [self.col_detector_center,
                                    self.row_detector_center],
                'centroid_success': self.centroid_success,
                'v2v3_measured': [self.v2_measured, self.v3_measured],
                'siaf_expected': [self.y_siaf_expected, self.x_siaf_expected],
                'v2v3_offsets': [self.v2_desired - self.v2_measured,
                                 self.v3_desired - self.v3_measured],
                'check_box_size': int(self.check_box_size),
                }
        output.update(extents)
        output.update({field: self[field] for field in fieldnames})
        return output
        
        