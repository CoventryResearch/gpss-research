"""
Contains helper functions to create figures and tables, based on the results of experiments.

@authors: David Duvenaud (dkd23@cam.ac.uk)
          James Robert Lloyd (jrl44@cam.ac.uk)
          Roger Grosse (rgrosse@mit.edu)
          
February 2013          
"""

import numpy as np
nax = np.newaxis
import os
import random
import scipy.io
import subprocess

import config
import experiment as exp
import flexiblekernel as fk
import gpml
import utils.latex
import re
import grammar
import translation

def compare_mse(folders, data_folder):
    if not isinstance(folders, list):
        folders = [folders] # Backward compatibility with specifying one folder
    data_sets = list(exp.gen_all_datasets(data_folder))
    for folder in folders:
        print ''
        print folder
        print ''
        # Load predictions file
        for r, data_file in data_sets:
            print '%s : ' % data_file,
            results_file = os.path.join(folder, data_file + "_predictions.mat")
            if os.path.isfile(results_file):
                data = scipy.io.loadmat(results_file)
                RMSE = np.sqrt(np.mean(np.power(data['predictions'].ravel() - data['actuals'].ravel(), 2)))
                print '%f' % RMSE
            else:
                print ''

def parse_all_results(folder, save_file='kernels.tex', one_d=False):
    """
    Creates a list of results, then sends them to be formatted into latex.
    """
    entries = [];
    rownames = [];
    
    colnames = ['Dataset', 'NLL', 'Kernel' ]
    for rt in gen_all_results(folder):
        print "dataset: %s kernel: %s\n" % (rt[0], rt[-1].pretty_print())
        if not one_d:
            entries.append([' %4.1f' % rt[-1].nll, ' $ %s $ ' % rt[-1].latex_print()])
        else:
            # Remove any underscored dimensions
            entries.append([' %4.1f' % rt[-1].nll, ' $ %s $ ' % re.sub('_{[0-9]+}', '', rt[-1].latex_print())])
        rownames.append(rt[0])
    
    utils.latex.table(''.join(['../latex/tables/', save_file]), rownames, colnames, entries)


def gen_all_results(folder):
    """Look through all the files in the results directory"""
    file_list = sorted([f for (r,d,f) in os.walk(folder)][0])
    #for r,d,f in os.walk(folder):
    for files in file_list:
        if files.endswith(".txt"):
            results_filename = os.path.join(folder,files)#r
            best_tuple = exp.parse_results( results_filename )
            yield files.split('.')[-2], best_tuple
                

def make_all_1d_figures(folders, save_folder='../figures/decomposition/', max_level=None, prefix='', rescale=True, data_folder=None, skip_kernel_evaluation=False):
    """Crawls the results directory, and makes decomposition plots for each file.
    
    prefix is an optional string prepended to the output directory
    """    
    
    if not isinstance(folders, list):
        folders = [folders] # Backward compatibility with specifying one folder
    #### Quick fix to axis scaling
    #### TODO - Ultimately this and the shunt below should be removed / made elegant
    if rescale:
        data_sets = list(exp.gen_all_datasets("../data/1d_data_rescaled/"))
    else:
        if data_folder is None:
            data_sets = list(exp.gen_all_datasets("../data/1d_data/"))
        else:
            data_sets = list(exp.gen_all_datasets(data_folder))
    for r, file in data_sets:
        results_files = []
        for folder in folders:
            results_file = os.path.join(folder, file + "_result.txt")
            if os.path.isfile(results_file):
                results_files.append(results_file)
        # Is the experiment complete
        if len(results_files) > 0:
            # Find best kernel and produce plots
            datafile = os.path.join(r,file + ".mat")
            X, y, D = gpml.load_mat(datafile)
            if rescale:
                # Load unscaled data to remove scaling later
                unscaled_file = os.path.join('../data/1d_data/', re.sub('-s$', '', file) + '.mat')
                data = gpml.load_mat(unscaled_file)
                (X_unscaled, y_unscaled) = (data[0], data[1])
                (X_mean, X_scale) = (X_unscaled.mean(), X_unscaled.std())
                (y_mean, y_scale) = (y_unscaled.mean(), y_unscaled.std())
            else:
                (X_mean, X_scale, y_mean, y_scale) = (0,1,0,1)
                
            # A shunt to deal with a legacy issue.
            if datafile == '../data/1d_data/01-airline-months.mat':
                # Scaling should turn months starting at zero into years starting at 1949
                print "Special rescaling for airline months data"
                X_mean = X_mean + 1949
                X_scale = 1.0/12.0
                                
            best_kernel = exp.parse_results(results_files, max_level=max_level)
            stripped_kernel = fk.strip_masks(best_kernel.k_opt)
            print stripped_kernel.pretty_print()
            stripped_kernel = grammar.canonical(fk.centre_periodic(stripped_kernel))
            print stripped_kernel.pretty_print()
            #stripped_kernel = grammar.canonical(fk.split_linear(stripped_kernel))
            #print stripped_kernel.pretty_print()
            stripped_kernel = grammar.canonical(fk.collapse_const_sums(stripped_kernel))
            print stripped_kernel.pretty_print()
            if not max_level is None:
                fig_folder = os.path.join(save_folder, (prefix + file + '_max_level_%d' % max_level))
            else:
                fig_folder = os.path.join(save_folder, (prefix + file))
            if not os.path.exists(fig_folder):
                os.makedirs(fig_folder)
            # Call gpml to plot the decomposition and evaluate the kernels
            (code, kernel_components) = gpml.plot_decomposition(stripped_kernel, X, y, os.path.join(fig_folder, file), best_kernel.noise, X_mean, X_scale, y_mean, y_scale, dont_run_code_hack=skip_kernel_evaluation)
            # Now the kernels have been evaluated we can translate the revelant ones
            evaluation_data = scipy.io.loadmat(os.path.join(fig_folder, '%s_decomp_data.mat' % file))
            component_order = evaluation_data['idx'].ravel() - 1 # MATLAB to python OBOE
            evaluation_data['vars'] = evaluation_data['vars'].ravel()
            evaluation_data['cum_vars'] = evaluation_data['cum_vars'].ravel()
            evaluation_data['cum_resid_vars'] = evaluation_data['cum_resid_vars'].ravel()
            evaluation_data['MAEs'] = evaluation_data['MAEs'].ravel()
            evaluation_data['MAE_reductions'] = evaluation_data['MAE_reductions'].ravel()
            evaluation_data['monotonic'] = evaluation_data['monotonic'].ravel()
            evaluation_data['acf_min_p'] = evaluation_data['acf_min_p'].ravel()
            evaluation_data['acf_min_loc_p'] = evaluation_data['acf_min_loc_p'].ravel()
            evaluation_data['pxx_max_p'] = evaluation_data['pxx_max_p'].ravel()
            evaluation_data['pxx_max_loc_p'] = evaluation_data['pxx_max_loc_p'].ravel()
            evaluation_data['qq_d_max_p'] = evaluation_data['qq_d_max_p'].ravel()
            evaluation_data['qq_d_min_p'] = evaluation_data['qq_d_min_p'].ravel()
            i = 1
            short_descriptions = []
            while os.path.isfile(os.path.join(fig_folder, '%s_%d.fig' % (file, i))):
                # Describe this component
                (summary, sentences, extrap_sentences) = translation.translate_additive_component(kernel_components[component_order[i-1]], X, evaluation_data['monotonic'][i-1], evaluation_data['gradients'][i-1], 'year')
                short_descriptions.append(summary)
                paragraph = '.\n'.join(sentences) + '.'
                extrap_paragraph = '.\n'.join(extrap_sentences) + '.'
                with open(os.path.join(fig_folder, '%s_%d_description.tex' % (file, i)), 'w') as description_file:
                    description_file.write(paragraph)
                with open(os.path.join(fig_folder, '%s_%d_extrap_description.tex' % (file, i)), 'w') as description_file:
                    description_file.write(extrap_paragraph)
                with open(os.path.join(fig_folder, '%s_%d_short_description.tex' % (file, i)), 'w') as description_file:
                    description_file.write(summary + '.')
                i += 1
            # Produce the summary LaTeX document
            latex_summary = translation.produce_summary_document(file, i-1, evaluation_data, short_descriptions)
            with open(os.path.join(save_folder, os.pardir, '%s.tex' % file), 'w') as latex_file:
                latex_file.write(latex_summary)
        else:
            print "Cannnot find results for %s" % file
            
def make_all_1d_figures_all_depths(folder, max_depth=10, **kwargs):
    make_all_1d_figures(folder=folder)
    for level in range(max_depth+1):
        make_all_1d_figures(folder=folder, max_level=level, **kwargs)
        
def figs_to_pdf():
    gpml.run_matlab_code('cd /scratch/home/Research/GPs/gpss-research/source/matlab\nfigs2pdf', verbose=True, jvm=True)
        
def compare_1d_decompositions():
    '''Produces the decomposition for all the files in the listed directories - to see which one to pick'''
    folders = ['../results/4-Feb-1d', 
               '../results/5-Feb-1d-NewLin', 
               '../results/5-Feb-1d-OldLin', 
               '../results/6-Feb-1d-More-Restarts', 
               '../results/6-Feb-1d-Even-More-Restarts', 
               '../results/8-Feb-1d-collated', 
               '../results/9-Feb-1d', 
               '../results/10-Feb-1d']
    for folder in folders:
        make_all_1d_figures(folder=folder, save_folder='../temp_figures/' + folder.split('/')[-1])
                
def make_kernel_description_table():
    '''A helper to generate a latex table listing all the kernels used, and their descriptions.'''
    entries = [];
    rownames = [];
    
    colnames = ['', 'Description', 'Parameters' ]
    for k in fk.base_kernel_families():
        # print "dataset: %s kernel: %s\n" % (rt[0], rt[-1].pretty_print())
        rownames.append( k.latex_print() )
        entries.append([ k.family().description(), k.family().params_description()])
    
    utils.latex.table('../latex/tables/kernel_descriptions.tex', rownames, colnames, entries, 'kernel_descriptions')
