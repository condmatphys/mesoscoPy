"""
Functions for characterisation of 2D Josehpson junctions
"""

from numpy import mean, fliplr, shape, zeros_like, arange, tile, array
from matplotlib import pyplot as plt

def mapping_SC(mat, index, N=10, threshold=None, returnA = False,div=2):
    '''extract the critical current for a map. Here the critical current is defined as 50% of Rn'''
    A = zeros_like(abs(mat))
    I, J = shape(A)

    for i in range(I):
        if threshold == None:
            threshold = mean(abs(mat)[i,0:N]) / div
        for j in range(J):
            if (abs(mat))[i,j] < threshold:
                A[i,j] = 1
            else:
                pass

    fig, ax = plt.subplots(figsize=(1,1))
    ax.pcolormesh(fliplr(A.T))
    ax.axis(False)

    if shape(index) == shape(mat):
        auxout = index
    elif len(index) == len(mat):
        t = arange(shape(mat)[1])
        auxout = tile(t, index)
    else:
        return IndexError ("index shape doesn't match with the size of the matrix.")

    ret = (find_ic(A, auxout, side=0),find_ic(A,auxout,side=1))

    if returnA:
        return ret, A
    else:
        return ret, None


def extract_zeros(array_in, threshold=10):
    '''array_in: np.array
    threshold: float, limit to extract zero resistance'''
    array_out = zeros_like(array_in)
    for i in range(shape(array_out)[0]):
        for j in range(shape(array_out)[1]):
            if abs(real(array_in[i,j])) < threshold:
                array_out[i, j] = 1
    return array_out


def find_ic(A,auxout,side=0):
    Ic = []
    for i in range(shape(A)[0]):
        vec1 = []
        vec2 = []
        for j in range(shape(A)[1]):
            #print(j)
            if A[i,j] == 1:
                vec1.append(auxout[i,j])
            elif A[i,j] == -1:
                vec2.append(auxout[i,j])
            else:
                vec1.append(0)
        if side == 0:
            pass
        else:
            vec1 = vec1[::-1]
            vec2 = vec2[::-1]
        try:
            m1 = max(vec1)
        except ValueError:
            m1 = 0
        try:
            m2 = max(vec2)
        except ValueError:
            m2 = 0
        if vec2 == []:
            Ic.append(m1)
        elif min(abs(array(vec2))) < m1:
            Ic.append(min(abs(array(vec2))))
        else:
            Ic.append(m1)
    return Ic
